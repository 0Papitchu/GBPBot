// Configuration des graphiques
const chartConfig = {
    type: 'line',
    options: {
        animation: false,
        responsive: true,
        scales: {
            x: {
                type: 'time',
                time: {
                    unit: 'minute'
                }
            }
        }
    }
};

// Initialisation des graphiques
const profitChart = new Chart(
    document.getElementById('profit-chart'),
    {
        ...chartConfig,
        data: {
            datasets: [{
                label: 'Cumulative Profit',
                borderColor: 'rgb(75, 192, 192)',
                tension: 0.1,
                data: []
            }]
        }
    }
);

const priceChart = new Chart(
    document.getElementById('price-chart'),
    {
        ...chartConfig,
        data: {
            datasets: [
                {
                    label: 'DEX Price',
                    borderColor: 'rgb(255, 99, 132)',
                    tension: 0.1,
                    data: []
                },
                {
                    label: 'CEX Price',
                    borderColor: 'rgb(54, 162, 235)',
                    tension: 0.1,
                    data: []
                }
            ]
        }
    }
);

// Gestion des WebSocket
class DashboardWebSocket {
    constructor() {
        this.connect();
        this.lastUpdate = new Date();
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.reconnectDelay = 1000;
    }

    connect() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        this.ws = new WebSocket(`${protocol}//${window.location.host}/ws`);
        
        this.ws.onopen = () => {
            console.log('WebSocket connected');
            document.getElementById('connection-status').className = 'badge bg-success';
            document.getElementById('connection-status').textContent = 'Connected';
            this.reconnectAttempts = 0;
            this.startHeartbeat();
        };
        
        this.ws.onclose = () => {
            console.log('WebSocket disconnected');
            document.getElementById('connection-status').className = 'badge bg-danger';
            document.getElementById('connection-status').textContent = 'Disconnected';
            this.reconnect();
        };
        
        this.ws.onerror = (error) => {
            console.error('WebSocket error:', error);
        };
        
        this.ws.onmessage = (event) => {
            this.handleMessage(event.data);
        };
    }

    reconnect() {
        if (this.reconnectAttempts >= this.maxReconnectAttempts) {
            console.error('Max reconnection attempts reached');
            return;
        }
        
        this.reconnectAttempts++;
        const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1);
        
        console.log(`Reconnecting in ${delay}ms...`);
        setTimeout(() => this.connect(), delay);
    }

    startHeartbeat() {
        setInterval(() => {
            if (this.ws.readyState === WebSocket.OPEN) {
                this.ws.send('ping');
            }
        }, 30000);
    }

    handleMessage(data) {
        try {
            const metrics = JSON.parse(data);
            this.updateMetrics(metrics);
        } catch (error) {
            console.error('Error parsing message:', error);
        }
    }

    updateMetrics(metrics) {
        this.lastUpdate = new Date();
        
        // Mise à jour des métriques de performance
        if (metrics.performance) {
            document.getElementById('total-profit').textContent = 
                `${metrics.performance.total_profit} ETH`;
            document.getElementById('success-rate').textContent = 
                `${(metrics.performance.success_rate * 100).toFixed(1)}%`;
                
            // Mise à jour du graphique de profit
            profitChart.data.datasets[0].data.push({
                x: this.lastUpdate,
                y: parseFloat(metrics.performance.total_profit)
            });
            
            if (profitChart.data.datasets[0].data.length > 100) {
                profitChart.data.datasets[0].data.shift();
            }
            profitChart.update('none');
        }
        
        // Mise à jour des données de marché
        if (metrics.market) {
            document.getElementById('dex-price').textContent = 
                parseFloat(metrics.market.dex_price).toFixed(2);
            document.getElementById('cex-price').textContent = 
                parseFloat(metrics.market.cex_price).toFixed(2);
            document.getElementById('spread').textContent = 
                `${(metrics.market.spread * 100).toFixed(3)}%`;
                
            // Mise à jour du graphique des prix
            priceChart.data.datasets[0].data.push({
                x: this.lastUpdate,
                y: parseFloat(metrics.market.dex_price)
            });
            priceChart.data.datasets[1].data.push({
                x: this.lastUpdate,
                y: parseFloat(metrics.market.cex_price)
            });
            
            if (priceChart.data.datasets[0].data.length > 100) {
                priceChart.data.datasets[0].data.shift();
                priceChart.data.datasets[1].data.shift();
            }
            priceChart.update('none');
        }
        
        // Mise à jour du statut système
        if (metrics.system) {
            document.getElementById('gas-price').textContent = 
                `${metrics.system.gas_price} Gwei`;
            document.getElementById('wallet-balance').textContent = 
                `${metrics.system.wallet_balance} ETH`;
        }
        
        // Mise à jour des alertes
        if (metrics.alerts && metrics.alerts.length > 0) {
            const alertsList = document.getElementById('alerts-list');
            metrics.alerts.forEach(alert => {
                const alertElement = document.createElement('div');
                alertElement.className = `alert alert-${alert.severity.toLowerCase()} mb-2`;
                alertElement.textContent = alert.message;
                
                alertsList.insertBefore(alertElement, alertsList.firstChild);
                if (alertsList.children.length > 5) {
                    alertsList.removeChild(alertsList.lastChild);
                }
            });
        }
        
        // Mise à jour des trades récents
        if (metrics.trades && metrics.trades.length > 0) {
            const tradesTable = document.getElementById('trades-table');
            metrics.trades.forEach(trade => {
                const row = document.createElement('tr');
                row.innerHTML = `
                    <td>${new Date(trade.timestamp).toLocaleTimeString()}</td>
                    <td>${trade.type}</td>
                    <td>${parseFloat(trade.amount).toFixed(4)}</td>
                    <td>${parseFloat(trade.price).toFixed(2)}</td>
                    <td class="${parseFloat(trade.profit) >= 0 ? 'text-success' : 'text-danger'}">
                        ${parseFloat(trade.profit).toFixed(4)}
                    </td>
                `;
                
                tradesTable.insertBefore(row, tradesTable.firstChild);
                if (tradesTable.children.length > 10) {
                    tradesTable.removeChild(tradesTable.lastChild);
                }
            });
        }
    }
}

// Démarrer la connexion WebSocket
const dashboard = new DashboardWebSocket(); 