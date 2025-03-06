import time
import json
import asyncio
import aiohttp
import statistics
from datetime import datetime

class DEXBenchmark:
    def __init__(self):
        self.results = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "solana": {
                "dex": {},
                "liquidity": {},
                "trading_pairs": {}
            }
        }
        
        # Définir les principales DEX Solana à analyser
        self.solana_dexes = {
            "raydium": {
                "name": "Raydium",
                "description": "Automated market maker (AMM) et liquidity provider sur Solana",
                "api_url": "https://api.raydium.io/v2/main/",
                "pairs_endpoint": "pairs"
            },
            "orca": {
                "name": "Orca",
                "description": "DEX centré sur l'expérience utilisateur",
                "api_url": "https://api.orca.so/",
                "pairs_endpoint": "pools"
            },
            "jupiter": {
                "name": "Jupiter Aggregator",
                "description": "Agrégateur de liquidité sur Solana",
                "api_url": "https://quote-api.jup.ag/v4/",
                "pairs_endpoint": "indexed-route-map"
            }
        }
        
        # Définir des paires de trading courantes pour tester les prix et la liquidité
        self.common_pairs = [
            {"base": "SOL", "quote": "USDC"},
            {"base": "SOL", "quote": "USDT"},
            {"base": "BTC", "quote": "USDC"},
            {"base": "ETH", "quote": "USDC"},
            {"base": "BONK", "quote": "USDC"},
            {"base": "JUP", "quote": "USDC"}
        ]
        
        # Meilleur RPC Solana (à remplacer par celui identifié dans le benchmark blockchain)
        self.solana_rpc = "https://api.mainnet-beta.solana.com"
        
    async def fetch_dex_info(self, dex_name, dex_info):
        """Récupère des informations générales sur le DEX"""
        results = {
            "name": dex_info["name"],
            "description": dex_info["description"],
            "api_url": dex_info["api_url"],
            "status": "unknown",
            "response_time": None,
            "error": None,
            "pairs_count": 0
        }
        
        try:
            start_time = time.time()
            pairs_url = f"{dex_info['api_url']}{dex_info['pairs_endpoint']}"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(pairs_url, timeout=10) as response:
                    if response.status == 200:
                        data = await response.json()
                        results["status"] = "online"
                        
                        # Tenter de compter le nombre de paires (la structure varie selon les DEX)
                        if isinstance(data, list):
                            results["pairs_count"] = len(data)
                        elif isinstance(data, dict) and "pairs" in data:
                            results["pairs_count"] = len(data["pairs"])
                        elif isinstance(data, dict) and "data" in data:
                            if isinstance(data["data"], list):
                                results["pairs_count"] = len(data["data"])
                            elif isinstance(data["data"], dict):
                                results["pairs_count"] = len(data["data"].keys())
                        elif isinstance(data, dict):
                            # Jupiter retourne une structure différente
                            if "mintKeys" in data or "indexedRouteMap" in data:
                                # Compter approximativement les paires pour Jupiter
                                results["pairs_count"] = len(data.get("mintKeys", data.get("indexedRouteMap", {})))
                    else:
                        results["status"] = f"error_{response.status}"
                        results["error"] = await response.text()
            
            end_time = time.time()
            results["response_time"] = end_time - start_time
            
        except Exception as e:
            results["status"] = "error"
            results["error"] = str(e)
            
        return dex_name, results
        
    async def check_price_and_liquidity(self, dex_name, dex_info, pair):
        """Vérifie le prix et la liquidité pour une paire donnée sur un DEX"""
        base_token = pair["base"]
        quote_token = pair["quote"]
        pair_name = f"{base_token}/{quote_token}"
        
        results = {
            "pair": pair_name,
            "dex": dex_name,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "available": False,
            "price": None,
            "liquidity": None,
            "volume_24h": None,
            "response_time": None,
            "error": None
        }
        
        try:
            start_time = time.time()
            
            # Les endpoints pour vérifier les prix varient selon le DEX
            # Ceci est un exemple simplifié
            if dex_name == "raydium":
                url = f"{dex_info['api_url']}pairs"
                async with aiohttp.ClientSession() as session:
                    async with session.get(url, timeout=10) as response:
                        if response.status == 200:
                            data = await response.json()
                            # Chercher la paire dans les données
                            for pair_data in data:
                                if (pair_data.get("name", "").upper() == f"{base_token}-{quote_token}") or \
                                   (pair_data.get("name", "").upper() == f"{base_token}/{quote_token}"):
                                    results["available"] = True
                                    results["price"] = float(pair_data.get("price", 0))
                                    results["liquidity"] = float(pair_data.get("liquidity", 0))
                                    results["volume_24h"] = float(pair_data.get("volume", 0))
                                    break
            
            elif dex_name == "orca":
                # Pour Orca, nous utilisons un endpoint différent
                url = f"{dex_info['api_url']}pools"
                async with aiohttp.ClientSession() as session:
                    async with session.get(url, timeout=10) as response:
                        if response.status == 200:
                            data = await response.json()
                            # Chercher la paire dans les données
                            for pool_id, pool_data in data.items():
                                pool_name = pool_data.get("name", "").upper()
                                if f"{base_token}/{quote_token}" in pool_name or f"{base_token}-{quote_token}" in pool_name:
                                    results["available"] = True
                                    # Calculer le prix à partir des tokens A et B
                                    if "tokenAPrice" in pool_data and "tokenBPrice" in pool_data:
                                        results["price"] = float(pool_data.get("tokenAPrice", 0))
                                    results["liquidity"] = float(pool_data.get("liquidity", 0))
                                    results["volume_24h"] = float(pool_data.get("volume", 0))
                                    break
            
            elif dex_name == "jupiter":
                # Pour Jupiter, nous utilisons l'API de quote
                url = f"{dex_info['api_url']}quote"
                params = {
                    "inputMint": self.token_to_mint(base_token),
                    "outputMint": self.token_to_mint(quote_token),
                    "amount": 1000000000,  # 1 SOL en lamports par exemple
                    "slippageBps": 50
                }
                
                async with aiohttp.ClientSession() as session:
                    async with session.get(url, params=params, timeout=10) as response:
                        if response.status == 200:
                            data = await response.json()
                            if "data" in data and "price" in data["data"]:
                                results["available"] = True
                                results["price"] = float(data["data"]["price"])
                                # Jupiter ne fournit pas directement la liquidité
                                results["liquidity"] = None
                                results["volume_24h"] = None
            
            end_time = time.time()
            results["response_time"] = end_time - start_time
            
        except Exception as e:
            results["error"] = str(e)
            
        return results
    
    def token_to_mint(self, token):
        """Convertit un symbole de token en adresse mint Solana (simplifié)"""
        # Ceci est une version simplifiée - en production, utilisez une vraie base de données de tokens
        token_mints = {
            "SOL": "So11111111111111111111111111111111111111112",
            "USDC": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
            "USDT": "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB",
            "BTC": "9n4nbM75f5Ui33ZbPYXn59EwSgE8CGsHtAeTH5YFeJ9E",  # BTC (Sollet)
            "ETH": "2FPyTwcZLUg1MDrwsyoP4D6s1tM7hAkHYRjkNb5w6Pxk",  # ETH (Sollet)
            "BONK": "DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263",
            "JUP": "JUPyiwrYJFskUPiHa7hkeR8VUtAeFoSYbKedZNsDvCN"
        }
        return token_mints.get(token.upper(), "")
    
    async def benchmark_dexes(self):
        """Benchmark complet des DEX Solana"""
        print("Benchmarking des DEX Solana...")
        
        # 1. Récupérer les informations générales sur chaque DEX
        dex_info_tasks = [
            self.fetch_dex_info(dex_name, dex_info) 
            for dex_name, dex_info in self.solana_dexes.items()
        ]
        dex_info_results = await asyncio.gather(*dex_info_tasks)
        
        for dex_name, results in dex_info_results:
            self.results["solana"]["dex"][dex_name] = results
            
        # 2. Vérifier les prix et la liquidité pour les paires communes
        all_liquidity_tasks = []
        
        for dex_name, dex_info in self.solana_dexes.items():
            for pair in self.common_pairs:
                task = self.check_price_and_liquidity(dex_name, dex_info, pair)
                all_liquidity_tasks.append(task)
                
        liquidity_results = await asyncio.gather(*all_liquidity_tasks)
        
        # Organiser les résultats par paire et par DEX
        for result in liquidity_results:
            pair = result["pair"]
            dex = result["dex"]
            
            if pair not in self.results["solana"]["trading_pairs"]:
                self.results["solana"]["trading_pairs"][pair] = {}
                
            self.results["solana"]["trading_pairs"][pair][dex] = result
            
        # 3. Analyse comparative
        self.analyze_dex_comparison()
        
        return self.results
    
    def analyze_dex_comparison(self):
        """Analyse les résultats et fournit une comparaison entre les DEX"""
        dex_metrics = {dex_name: {
            "response_times": [],
            "available_pairs": 0,
            "total_pairs_checked": 0,
            "price_variance": []
        } for dex_name in self.solana_dexes.keys()}
        
        pair_metrics = {}
        
        # Collecter les métriques
        for pair_name, dex_data in self.results["solana"]["trading_pairs"].items():
            pair_metrics[pair_name] = {"prices": {}, "response_times": {}}
            
            for dex_name, data in dex_data.items():
                dex_metrics[dex_name]["total_pairs_checked"] += 1
                
                if data["available"]:
                    dex_metrics[dex_name]["available_pairs"] += 1
                    
                if data["response_time"]:
                    dex_metrics[dex_name]["response_times"].append(data["response_time"])
                    pair_metrics[pair_name]["response_times"][dex_name] = data["response_time"]
                    
                if data["price"]:
                    pair_metrics[pair_name]["prices"][dex_name] = data["price"]
                    
        # Calculer les variances de prix entre DEX
        for pair_name, metrics in pair_metrics.items():
            prices = list(metrics["prices"].values())
            if len(prices) >= 2:
                for dex_name in metrics["prices"].keys():
                    if prices:
                        avg_price = sum(prices) / len(prices)
                        if avg_price > 0:
                            variance = abs(metrics["prices"][dex_name] - avg_price) / avg_price
                            dex_metrics[dex_name]["price_variance"].append(variance)
        
        # Calculer les moyennes et préparer le résumé
        comparison = {
            "response_time_ranking": [],
            "price_deviation_ranking": [],
            "availability_ranking": [],
            "overall_ranking": []
        }
        
        # Classement par temps de réponse
        response_time_scores = {}
        for dex_name, metrics in dex_metrics.items():
            if metrics["response_times"]:
                avg_response_time = statistics.mean(metrics["response_times"])
                response_time_scores[dex_name] = 1.0 / avg_response_time  # Plus petit = meilleur score
        
        comparison["response_time_ranking"] = sorted(
            response_time_scores.items(), 
            key=lambda x: x[1], 
            reverse=True
        )
        
        # Classement par déviation de prix
        price_deviation_scores = {}
        for dex_name, metrics in dex_metrics.items():
            if metrics["price_variance"]:
                avg_variance = statistics.mean(metrics["price_variance"])
                price_deviation_scores[dex_name] = 1.0 / (avg_variance + 0.0001)  # Plus petit = meilleur score
        
        comparison["price_deviation_ranking"] = sorted(
            price_deviation_scores.items(), 
            key=lambda x: x[1], 
            reverse=True
        )
        
        # Classement par disponibilité
        availability_scores = {}
        for dex_name, metrics in dex_metrics.items():
            if metrics["total_pairs_checked"] > 0:
                availability_scores[dex_name] = metrics["available_pairs"] / metrics["total_pairs_checked"]
        
        comparison["availability_ranking"] = sorted(
            availability_scores.items(), 
            key=lambda x: x[1], 
            reverse=True
        )
        
        # Classement global (combinaison des trois scores précédents)
        overall_scores = {}
        for dex_name in self.solana_dexes.keys():
            score = 0
            count = 0
            
            if dex_name in response_time_scores:
                score += response_time_scores[dex_name]
                count += 1
                
            if dex_name in price_deviation_scores:
                score += price_deviation_scores[dex_name] * 2  # Poids plus important pour la précision des prix
                count += 2
                
            if dex_name in availability_scores:
                score += availability_scores[dex_name] * 3  # Poids encore plus important pour la disponibilité
                count += 3
                
            if count > 0:
                overall_scores[dex_name] = score / count
        
        comparison["overall_ranking"] = sorted(
            overall_scores.items(), 
            key=lambda x: x[1], 
            reverse=True
        )
        
        self.results["solana"]["comparison"] = comparison
        
    async def run_benchmark(self):
        """Exécute tous les benchmarks"""
        await self.benchmark_dexes()
        return self.results
        
    def save_results(self, filename="dex_benchmark_results.json"):
        """Sauvegarde les résultats dans un fichier JSON"""
        with open(filename, 'w') as f:
            json.dump(self.results, f, indent=4)
        print(f"Résultats sauvegardés dans {filename}")
        
    def print_summary(self):
        """Affiche un résumé des résultats"""
        print("\n" + "="*50)
        print("RÉSUMÉ DU BENCHMARK DES DEX")
        print("="*50)
        
        # Afficher les informations générales
        print("\nInformations générales sur les DEX:")
        for dex_name, info in self.results["solana"]["dex"].items():
            status = info["status"]
            pairs_count = info["pairs_count"]
            response_time = info["response_time"]
            
            status_str = "✅ En ligne" if status == "online" else f"❌ Hors ligne ({status})"
            time_str = f"{response_time:.4f}s" if response_time else "N/A"
            
            print(f"- {info['name']}: {status_str}, {pairs_count} paires, temps de réponse: {time_str}")
            
        # Afficher les classements
        if "comparison" in self.results["solana"]:
            comp = self.results["solana"]["comparison"]
            
            print("\nClassement par temps de réponse:")
            for i, (dex_name, score) in enumerate(comp["response_time_ranking"]):
                print(f"{i+1}. {self.solana_dexes[dex_name]['name']} (score: {score:.2f})")
                
            print("\nClassement par précision des prix:")
            for i, (dex_name, score) in enumerate(comp["price_deviation_ranking"]):
                print(f"{i+1}. {self.solana_dexes[dex_name]['name']} (score: {score:.2f})")
                
            print("\nClassement par disponibilité des paires:")
            for i, (dex_name, score) in enumerate(comp["availability_ranking"]):
                print(f"{i+1}. {self.solana_dexes[dex_name]['name']} (score: {score:.2f})")
                
            print("\nClassement global des DEX:")
            for i, (dex_name, score) in enumerate(comp["overall_ranking"]):
                print(f"{i+1}. {self.solana_dexes[dex_name]['name']} (score: {score:.2f})")
                
        # Afficher les informations sur les paires de trading
        print("\nPaires de trading analysées:")
        for pair_name, dex_data in self.results["solana"]["trading_pairs"].items():
            print(f"\n{pair_name}:")
            
            for dex_name, data in dex_data.items():
                if data["available"]:
                    price_str = f"Prix: {data['price']}" if data["price"] else "Prix: N/A"
                    liquidity_str = f"Liquidité: {data['liquidity']}" if data["liquidity"] else "Liquidité: N/A"
                    time_str = f"Temps: {data['response_time']:.4f}s" if data["response_time"] else "Temps: N/A"
                    
                    print(f"  - {self.solana_dexes[dex_name]['name']}: {price_str}, {liquidity_str}, {time_str}")
                else:
                    print(f"  - {self.solana_dexes[dex_name]['name']}: Non disponible")
                    
        print("\nRecommandation: Utiliser le DEX classé #1 pour des performances optimales.")
        print("="*50)

async def main():
    benchmark = DEXBenchmark()
    await benchmark.run_benchmark()
    benchmark.save_results("benchmarking/dex_benchmark_results.json")
    benchmark.print_summary()

if __name__ == "__main__":
    asyncio.run(main()) 