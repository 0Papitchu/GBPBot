/**
 * GBPBot Dashboard - Application Vue.js
 * 
 * Ce fichier contient l'application Vue.js qui gère l'interface utilisateur
 * du dashboard GBPBot et la communication avec le serveur backend.
 */

// Création de l'application Vue
const app = Vue.createApp({
    data() {
        return {
            // Navigation et état
            activePage: 'dashboard',
            connectionStatus: {
                connected: false,
                text: 'Déconnecté',
                icon: 'bi-wifi-off text-danger'
            },
            botStatus: {
                running: false,
                text: 'Arrêté',
                class: 'text-danger'
            },
            
            // Dashboard
            totalBalance: 0,
            dailyProfitPct: 0,
            dailyTrades: 0,
            dailySuccessfulTrades: 0,
            dailyFailedTrades: 0,
            opportunities: [],
            executedOpportunities: 0,
            pendingOpportunities: 0,
            activeStrategies: [],
            uptime: '0h 0m',
            timeframe: 'day',
            recentOpportunities: [],
            recentTrades: [],
            
            // Stratégies
            availableStrategies: [],
            selectedStrategy: null,
            strategyParams: {},
            
            // Backtesting
            backtestConfig: {
                strategy_name: '',
                parameters: {},
                symbols: [],
                start_date: this.getDefaultStartDate(),
                end_date: this.getDefaultEndDate(),
                timeframe: '1h',
                data_source: 'binance',
                initial_balance: { 'USDT': 1000 }
            },
            backtestSymbols: 'BTC/USDT,ETH/USDT',
            initialBalanceUSDT: 1000,
            backtestResults: null,
            backtestHistory: [],
            
            // WebSocket
            socket: null,
            reconnectInterval: null,
            
            // Charts
            performanceChart: null,
            balanceChart: null,
            backtestChart: null
        };
    },
    computed: {
        profitClass() {
            return this.dailyProfitPct >= 0 ? 'text-success' : 'text-danger';
        },
        profitIcon() {
            return this.dailyProfitPct >= 0 ? 'bi bi-arrow-up-right' : 'bi bi-arrow-down-right';
        }
    },
    methods: {
        // Navigation
        setActivePage(page) {
            this.activePage = page;
            
            // Initialiser les données spécifiques à la page
            if (page === 'strategies' && this.availableStrategies.length === 0) {
                this.loadStrategies();
            } else if (page === 'backtest' && this.backtestHistory.length === 0) {
                this.loadBacktestHistory();
            }
            
            // Mettre à jour les graphiques après le rendu
            this.$nextTick(() => {
                if (page === 'dashboard') {
                    this.initPerformanceChart();
                    this.initBalanceChart();
                } else if (page === 'backtest' && this.backtestResults) {
                    this.initBacktestChart();
                }
            });
        },
        
        // Formatage
        formatCurrency(value) {
            return new Intl.NumberFormat('fr-FR', {
                style: 'currency',
                currency: 'USD',
                minimumFractionDigits: 2,
                maximumFractionDigits: 2
            }).format(value);
        },
        formatPercentage(value) {
            return new Intl.NumberFormat('fr-FR', {
                style: 'percent',
                minimumFractionDigits: 2,
                maximumFractionDigits: 2
            }).format(value / 100);
        },
        formatTime(timestamp) {
            if (!timestamp) return '';
            const date = new Date(timestamp);
            return date.toLocaleTimeString('fr-FR', {
                hour: '2-digit',
                minute: '2-digit',
                second: '2-digit'
            });
        },
        formatDate(dateStr) {
            if (!dateStr) return '';
            const date = new Date(dateStr);
            return date.toLocaleDateString('fr-FR');
        },
        formatParameterName(key) {
            // Convertir snake_case en texte lisible
            return key.split('_').map(word => word.charAt(0).toUpperCase() + word.slice(1)).join(' ');
        },
        getInputType(value) {
            if (typeof value === 'number') {
                return 'number';
            } else if (typeof value === 'boolean') {
                return 'checkbox';
            } else {
                return 'text';
            }
        },
        timeframeClass(tf) {
            return this.timeframe === tf ? 'btn-primary' : 'btn-outline-primary';
        },
        setTimeframe(tf) {
            this.timeframe = tf;
            this.updatePerformanceChart();
        },
        opportunityStatusClass(status) {
            switch (status) {
                case 'executed': return 'bg-success';
                case 'pending': return 'bg-warning';
                case 'failed': return 'bg-danger';
                default: return 'bg-secondary';
            }
        },
        strategyStatusClass(status) {
            switch (status) {
                case 'running': return 'bg-success';
                case 'paused': return 'bg-warning';
                case 'stopped': return 'bg-danger';
                default: return 'bg-secondary';
            }
        },
        
        // Dates par défaut pour le backtesting
        getDefaultStartDate() {
            const date = new Date();
            date.setMonth(date.getMonth() - 1);
            return date.toISOString().split('T')[0];
        },
        getDefaultEndDate() {
            return new Date().toISOString().split('T')[0];
        },
        
        // API Calls
        async loadStatus() {
            try {
                const response = await axios.get('/api/status');
                const data = response.data;
                
                this.botStatus.running = data.running;
                this.botStatus.text = data.running ? 'En cours' : 'Arrêté';
                this.botStatus.class = data.running ? 'text-success' : 'text-danger';
                
                this.activeStrategies = data.active_modules.map(module => ({
                    name: module,
                    start_time: new Date().toISOString(),
                    status: 'running'
                }));
                
                // Mise à jour des données de performance
                if (data.performance) {
                    this.totalBalance = data.performance.total_profit || 0;
                    this.dailyProfitPct = data.performance.daily_profit_pct || 0;
                    this.dailyTrades = data.performance.trades_count || 0;
                    this.dailySuccessfulTrades = Math.round(this.dailyTrades * (data.performance.win_rate || 0) / 100);
                    this.dailyFailedTrades = this.dailyTrades - this.dailySuccessfulTrades;
                }
            } catch (error) {
                console.error('Erreur lors du chargement du statut:', error);
            }
        },
        
        async loadStrategies() {
            try {
                const response = await axios.get('/api/strategies');
                this.availableStrategies = response.data.strategies || [];
                
                if (this.availableStrategies.length > 0) {
                    this.selectStrategy(this.availableStrategies[0]);
                }
            } catch (error) {
                console.error('Erreur lors du chargement des stratégies:', error);
            }
        },
        
        selectStrategy(strategy) {
            this.selectedStrategy = strategy;
            this.strategyParams = { ...strategy.parameters };
        },
        
        async startStrategy() {
            try {
                const response = await axios.post('/api/strategies/start', {
                    strategy_name: this.selectedStrategy.name,
                    parameters: this.strategyParams
                });
                
                if (response.data.status === 'success') {
                    alert(`Stratégie ${this.selectedStrategy.name} démarrée avec succès!`);
                    this.loadStatus();
                }
            } catch (error) {
                console.error('Erreur lors du démarrage de la stratégie:', error);
                alert(`Erreur: ${error.response?.data?.detail || error.message}`);
            }
        },
        
        async stopStrategy(strategyName) {
            try {
                const response = await axios.post('/api/strategies/stop', {
                    strategy_name: strategyName,
                    parameters: {}
                });
                
                if (response.data.status === 'success') {
                    alert(`Stratégie ${strategyName} arrêtée avec succès!`);
                    this.loadStatus();
                }
            } catch (error) {
                console.error('Erreur lors de l\'arrêt de la stratégie:', error);
                alert(`Erreur: ${error.response?.data?.detail || error.message}`);
            }
        },
        
        async runBacktest() {
            try {
                // Préparer les paramètres
                this.backtestConfig.symbols = this.backtestSymbols.split(',').map(s => s.trim());
                this.backtestConfig.initial_balance = { 'USDT': parseFloat(this.initialBalanceUSDT) };
                
                const response = await axios.post('/api/backtest', this.backtestConfig);
                
                if (response.data.status === 'success') {
                    this.backtestResults = response.data.results;
                    this.initBacktestChart();
                    
                    // Ajouter au historique
                    this.backtestHistory.unshift({
                        id: Date.now().toString(),
                        date: new Date().toISOString(),
                        strategy: this.backtestConfig.strategy_name,
                        symbols: this.backtestConfig.symbols,
                        start_date: this.backtestConfig.start_date,
                        end_date: this.backtestConfig.end_date,
                        return: this.backtestResults.total_return
                    });
                }
            } catch (error) {
                console.error('Erreur lors de l\'exécution du backtest:', error);
                alert(`Erreur: ${error.response?.data?.detail || error.message}`);
            }
        },
        
        async loadBacktestHistory() {
            try {
                const response = await axios.get('/api/backtests');
                this.backtestHistory = response.data.backtests || [];
            } catch (error) {
                console.error('Erreur lors du chargement de l\'historique des backtests:', error);
            }
        },
        
        viewBacktestDetails(backtest) {
            // Charger les détails du backtest
            axios.get(`/api/backtest/${backtest.id}`)
                .then(response => {
                    if (response.data.status === 'success') {
                        this.backtestResults = response.data.results;
                        this.initBacktestChart();
                    }
                })
                .catch(error => {
                    console.error('Erreur lors du chargement des détails du backtest:', error);
                });
        },
        
        // WebSocket
        setupWebSocket() {
            // Fermer la connexion existante si elle existe
            if (this.socket) {
                this.socket.close();
            }
            
            // Créer une nouvelle connexion WebSocket
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            const wsUrl = `${protocol}//${window.location.host}/ws`;
            
            this.socket = new WebSocket(wsUrl);
            
            this.socket.onopen = () => {
                console.log('WebSocket connecté');
                this.connectionStatus.connected = true;
                this.connectionStatus.text = 'Connecté';
                this.connectionStatus.icon = 'bi-wifi text-success';
                
                // Arrêter la tentative de reconnexion si elle est en cours
                if (this.reconnectInterval) {
                    clearInterval(this.reconnectInterval);
                    this.reconnectInterval = null;
                }
            };
            
            this.socket.onclose = () => {
                console.log('WebSocket déconnecté');
                this.connectionStatus.connected = false;
                this.connectionStatus.text = 'Déconnecté';
                this.connectionStatus.icon = 'bi-wifi-off text-danger';
                
                // Tenter de se reconnecter toutes les 5 secondes
                if (!this.reconnectInterval) {
                    this.reconnectInterval = setInterval(() => {
                        console.log('Tentative de reconnexion WebSocket...');
                        this.setupWebSocket();
                    }, 5000);
                }
            };
            
            this.socket.onerror = (error) => {
                console.error('Erreur WebSocket:', error);
            };
            
            this.socket.onmessage = (event) => {
                try {
                    const message = JSON.parse(event.data);
                    this.handleWebSocketMessage(message);
                } catch (error) {
                    console.error('Erreur lors du traitement du message WebSocket:', error);
                }
            };
        },
        
        handleWebSocketMessage(message) {
            console.log('Message WebSocket reçu:', message);
            
            switch (message.type) {
                case 'initial_state':
                    this.updateBotState(message.data);
                    break;
                
                case 'strategy_update':
                    this.handleStrategyUpdate(message.data);
                    break;
                
                case 'performance_update':
                    this.updatePerformanceData(message.data);
                    break;
                
                case 'opportunity_detected':
                    this.handleNewOpportunity(message.data);
                    break;
                
                case 'trade_executed':
                    this.handleNewTrade(message.data);
                    break;
            }
        },
        
        updateBotState(data) {
            this.botStatus.running = data.running;
            this.botStatus.text = data.running ? 'En cours' : 'Arrêté';
            this.botStatus.class = data.running ? 'text-success' : 'text-danger';
            
            this.activeStrategies = data.active_modules.map(module => ({
                name: module,
                start_time: data.last_update,
                status: 'running'
            }));
            
            if (data.performance) {
                this.updatePerformanceData(data.performance);
            }
        },
        
        handleStrategyUpdate(data) {
            if (data.status === 'started') {
                // Ajouter la stratégie si elle n'existe pas déjà
                if (!this.activeStrategies.some(s => s.name === data.strategy)) {
                    this.activeStrategies.push({
                        name: data.strategy,
                        start_time: new Date().toISOString(),
                        status: 'running'
                    });
                }
            } else if (data.status === 'stopped') {
                // Supprimer la stratégie de la liste des stratégies actives
                this.activeStrategies = this.activeStrategies.filter(s => s.name !== data.strategy);
            }
            
            // Mettre à jour le statut du bot
            this.botStatus.running = this.activeStrategies.length > 0;
            this.botStatus.text = this.botStatus.running ? 'En cours' : 'Arrêté';
            this.botStatus.class = this.botStatus.running ? 'text-success' : 'text-danger';
        },
        
        updatePerformanceData(data) {
            this.totalBalance = data.total_profit || 0;
            this.dailyProfitPct = data.daily_profit_pct || 0;
            this.dailyTrades = data.trades_count || 0;
            this.dailySuccessfulTrades = Math.round(this.dailyTrades * (data.win_rate || 0) / 100);
            this.dailyFailedTrades = this.dailyTrades - this.dailySuccessfulTrades;
            
            // Mettre à jour le graphique de performance si disponible
            if (this.performanceChart) {
                this.updatePerformanceChart();
            }
        },
        
        handleNewOpportunity(opportunity) {
            // Ajouter l'opportunité à la liste
            this.opportunities.push(opportunity);
            
            // Mettre à jour les compteurs
            this.executedOpportunities = this.opportunities.filter(o => o.status === 'executed').length;
            this.pendingOpportunities = this.opportunities.filter(o => o.status === 'pending').length;
            
            // Mettre à jour la liste des opportunités récentes
            this.recentOpportunities = this.opportunities.slice(-5).reverse();
        },
        
        handleNewTrade(trade) {
            // Ajouter le trade à la liste des trades récents
            this.recentTrades.unshift(trade);
            
            // Limiter la liste à 5 éléments
            if (this.recentTrades.length > 5) {
                this.recentTrades.pop();
            }
        },
        
        // Charts
        initPerformanceChart() {
            const ctx = document.getElementById('performanceChart');
            if (!ctx) return;
            
            // Détruire le graphique existant s'il existe
            if (this.performanceChart) {
                this.performanceChart.destroy();
            }
            
            // Données de démonstration
            const labels = Array.from({ length: 24 }, (_, i) => `${i}:00`);
            const data = Array.from({ length: 24 }, () => Math.random() * 10 - 2);
            
            // Créer le graphique
            this.performanceChart = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: labels,
                    datasets: [{
                        label: 'Performance',
                        data: data,
                        borderColor: '#0d6efd',
                        backgroundColor: 'rgba(13, 110, 253, 0.1)',
                        fill: true,
                        tension: 0.4
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            display: false
                        },
                        tooltip: {
                            mode: 'index',
                            intersect: false
                        }
                    },
                    scales: {
                        x: {
                            grid: {
                                display: false
                            }
                        },
                        y: {
                            grid: {
                                color: 'rgba(0, 0, 0, 0.05)'
                            }
                        }
                    }
                }
            });
        },
        
        updatePerformanceChart() {
            if (!this.performanceChart) return;
            
            // Mettre à jour les données en fonction du timeframe
            let labels, data;
            
            switch (this.timeframe) {
                case 'day':
                    labels = Array.from({ length: 24 }, (_, i) => `${i}:00`);
                    data = Array.from({ length: 24 }, () => Math.random() * 10 - 2);
                    break;
                case 'week':
                    labels = ['Lun', 'Mar', 'Mer', 'Jeu', 'Ven', 'Sam', 'Dim'];
                    data = Array.from({ length: 7 }, () => Math.random() * 20 - 5);
                    break;
                case 'month':
                    labels = Array.from({ length: 30 }, (_, i) => `${i+1}`);
                    data = Array.from({ length: 30 }, () => Math.random() * 30 - 10);
                    break;
            }
            
            this.performanceChart.data.labels = labels;
            this.performanceChart.data.datasets[0].data = data;
            this.performanceChart.update();
        },
        
        initBalanceChart() {
            const ctx = document.getElementById('balanceChart');
            if (!ctx) return;
            
            // Détruire le graphique existant s'il existe
            if (this.balanceChart) {
                this.balanceChart.destroy();
            }
            
            // Données de démonstration
            const data = {
                labels: ['USDT', 'BTC', 'ETH', 'SOL', 'AVAX'],
                datasets: [{
                    data: [60, 15, 10, 10, 5],
                    backgroundColor: [
                        '#28a745', // USDT
                        '#f7931a', // BTC
                        '#627eea', // ETH
                        '#00ffbd', // SOL
                        '#e84142'  // AVAX
                    ],
                    borderWidth: 1
                }]
            };
            
            // Créer le graphique
            this.balanceChart = new Chart(ctx, {
                type: 'doughnut',
                data: data,
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            position: 'right'
                        }
                    }
                }
            });
        },
        
        initBacktestChart() {
            const ctx = document.getElementById('backtestChart');
            if (!ctx || !this.backtestResults) return;
            
            // Détruire le graphique existant s'il existe
            if (this.backtestChart) {
                this.backtestChart.destroy();
            }
            
            // Données du backtest
            const equityCurve = this.backtestResults.equity_curve || [];
            const labels = equityCurve.map(point => new Date(point.timestamp).toLocaleDateString());
            const data = equityCurve.map(point => point.equity);
            
            // Créer le graphique
            this.backtestChart = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: labels,
                    datasets: [{
                        label: 'Équité',
                        data: data,
                        borderColor: '#0d6efd',
                        backgroundColor: 'rgba(13, 110, 253, 0.1)',
                        fill: true,
                        tension: 0.1
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            display: false
                        },
                        tooltip: {
                            mode: 'index',
                            intersect: false,
                            callbacks: {
                                label: (context) => {
                                    return `Équité: ${this.formatCurrency(context.raw)}`;
                                }
                            }
                        }
                    },
                    scales: {
                        x: {
                            grid: {
                                display: false
                            },
                            ticks: {
                                maxTicksLimit: 10
                            }
                        },
                        y: {
                            grid: {
                                color: 'rgba(0, 0, 0, 0.05)'
                            }
                        }
                    }
                }
            });
        }
    },
    mounted() {
        // Charger les données initiales
        this.loadStatus();
        
        // Initialiser les graphiques
        this.$nextTick(() => {
            this.initPerformanceChart();
            this.initBalanceChart();
        });
        
        // Configurer la connexion WebSocket
        this.setupWebSocket();
        
        // Simuler des données pour la démo
        this.recentOpportunities = [
            {
                id: 'opp_1',
                timestamp: new Date().toISOString(),
                type: 'arbitrage',
                symbol: 'BTC/USDT',
                spread_pct: 0.5,
                estimated_profit: 25.0,
                status: 'executed'
            },
            {
                id: 'opp_2',
                timestamp: new Date(Date.now() - 60000).toISOString(),
                type: 'arbitrage',
                symbol: 'ETH/USDT',
                spread_pct: 0.3,
                estimated_profit: 15.0,
                status: 'pending'
            }
        ];
        
        this.recentTrades = [
            {
                id: 'trade_1',
                timestamp: new Date().toISOString(),
                symbol: 'BTC/USDT',
                side: 'buy',
                price: 50000,
                amount: 0.1,
                value: 5000
            },
            {
                id: 'trade_2',
                timestamp: new Date(Date.now() - 120000).toISOString(),
                symbol: 'ETH/USDT',
                side: 'sell',
                price: 3000,
                amount: 1.5,
                value: 4500
            }
        ];
    }
});

// Monter l'application
app.mount('#app'); 