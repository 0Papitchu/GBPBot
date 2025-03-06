import time
import json
import asyncio
import aiohttp
import statistics
from datetime import datetime, timedelta
import random
import base64

class TransactionBenchmark:
    def __init__(self):
        self.results = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "solana": {
                "transaction_speed": {},
                "block_time": [],
                "mev_analysis": {},
                "confirmation_times": {}
            }
        }
        
        # Liste des RPCs Solana (utiliser les meilleurs identifiés dans le benchmark blockchain)
        self.solana_rpcs = {
            "mainnet": "https://api.mainnet-beta.solana.com",
            "quicknode": "https://solana-mainnet.quicknode.com",
            "genesysgo": "https://ssc-dao.genesysgo.net"
        }
        
        # Préfixe pour les requêtes JSON-RPC
        self.rpc_id = 0
        
        # Nombre de blocs à analyser pour le temps de bloc
        self.blocks_to_analyze = 100
        
        # Nombre de transactions à analyser pour les confirmations
        self.txs_to_analyze = 50
        
    async def get_latest_block(self, rpc_url):
        """Récupère le dernier bloc de la blockchain Solana"""
        self.rpc_id += 1
        
        payload = {
            "jsonrpc": "2.0",
            "id": self.rpc_id,
            "method": "getSlot",
            "params": [{"commitment": "finalized"}]
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(rpc_url, json=payload, timeout=10) as response:
                    if response.status == 200:
                        result = await response.json()
                        if "result" in result:
                            return result["result"]
        except Exception as e:
            print(f"Erreur lors de la récupération du dernier bloc: {str(e)}")
            
        return None
    
    async def get_block(self, rpc_url, slot):
        """Récupère les informations d'un bloc spécifique"""
        self.rpc_id += 1
        
        payload = {
            "jsonrpc": "2.0",
            "id": self.rpc_id,
            "method": "getBlock",
            "params": [
                slot,
                {
                    "encoding": "json",
                    "maxSupportedTransactionVersion": 0,
                    "transactionDetails": "full"
                }
            ]
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(rpc_url, json=payload, timeout=15) as response:
                    if response.status == 200:
                        result = await response.json()
                        if "result" in result:
                            return result["result"]
        except Exception as e:
            print(f"Erreur lors de la récupération du bloc {slot}: {str(e)}")
            
        return None
    
    async def get_transaction(self, rpc_url, signature):
        """Récupère les détails d'une transaction"""
        self.rpc_id += 1
        
        payload = {
            "jsonrpc": "2.0",
            "id": self.rpc_id,
            "method": "getTransaction",
            "params": [
                signature,
                {"encoding": "json", "maxSupportedTransactionVersion": 0}
            ]
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(rpc_url, json=payload, timeout=10) as response:
                    if response.status == 200:
                        result = await response.json()
                        if "result" in result:
                            return result["result"]
        except Exception as e:
            print(f"Erreur lors de la récupération de la transaction {signature}: {str(e)}")
            
        return None
    
    async def measure_block_time(self, rpc_url=None):
        """Mesure le temps moyen entre les blocs"""
        if rpc_url is None:
            rpc_url = self.solana_rpcs["mainnet"]
            
        print(f"Mesure du temps de bloc sur {self.blocks_to_analyze} blocs...")
        
        # Récupérer le dernier bloc confirmé
        latest_slot = await self.get_latest_block(rpc_url)
        if latest_slot is None:
            print("Impossible de récupérer le dernier bloc")
            return []
            
        block_times = []
        blocks_info = []
        
        # Récupérer les informations des derniers blocs
        slots_to_check = [latest_slot - i for i in range(self.blocks_to_analyze + 10)]
        
        for slot in slots_to_check[:20]:  # Limiter pour éviter trop de requêtes
            block = await self.get_block(rpc_url, slot)
            if block and "blockTime" in block:
                blocks_info.append({
                    "slot": slot,
                    "blockTime": block["blockTime"],
                    "transactions": len(block.get("transactions", []))
                })
                
        # Trier par slot pour s'assurer de l'ordre chronologique
        blocks_info.sort(key=lambda b: b["slot"])
        
        # Calculer le temps entre les blocs
        for i in range(1, len(blocks_info)):
            prev_block = blocks_info[i-1]
            curr_block = blocks_info[i]
            
            time_diff = curr_block["blockTime"] - prev_block["blockTime"]
            block_times.append({
                "prev_slot": prev_block["slot"],
                "curr_slot": curr_block["slot"],
                "time_diff": time_diff,
                "transactions": curr_block["transactions"]
            })
            
        # Filtrer les valeurs aberrantes (temps > 5 secondes)
        filtered_times = [bt["time_diff"] for bt in block_times if bt["time_diff"] < 5]
        
        if filtered_times:
            avg_block_time = statistics.mean(filtered_times)
            median_block_time = statistics.median(filtered_times)
            
            self.results["solana"]["block_time"] = {
                "average": avg_block_time,
                "median": median_block_time,
                "min": min(filtered_times),
                "max": max(filtered_times),
                "samples": len(filtered_times)
            }
            
            return block_times
            
        return []
    
    async def analyze_transaction_speed(self, rpc_url=None):
        """Analyse la vitesse des transactions et le temps de confirmation"""
        if rpc_url is None:
            rpc_url = self.solana_rpcs["mainnet"]
            
        print("Analyse des temps de confirmation des transactions...")
        
        # Récupérer le dernier bloc confirmé
        latest_slot = await self.get_latest_block(rpc_url)
        if latest_slot is None:
            print("Impossible de récupérer le dernier bloc")
            return
            
        # Récupérer des blocs récents
        blocks = []
        signatures = []
        
        for i in range(5):
            block = await self.get_block(rpc_url, latest_slot - i)
            if block and "transactions" in block:
                blocks.append(block)
                # Collecter les signatures des transactions
                for tx in block["transactions"]:
                    if "transaction" in tx and "signatures" in tx["transaction"]:
                        signatures.extend(tx["transaction"]["signatures"])
                        
        # Limiter le nombre de transactions à analyser
        if signatures:
            random.shuffle(signatures)
            signatures = signatures[:min(self.txs_to_analyze, len(signatures))]
            
            # Analyser chaque transaction
            confirmation_times = []
            
            for sig in signatures[:10]:  # Limiter pour éviter trop de requêtes
                tx_data = await self.get_transaction(rpc_url, sig)
                if tx_data and "blockTime" in tx_data:
                    # Calculer le temps de confirmation (approximatif)
                    if "meta" in tx_data and "err" is tx_data["meta"]:
                        confirmation_status = "success" if tx_data["meta"]["err"] is None else "failed"
                        slots_to_confirm = tx_data.get("meta", {}).get("confirmations", 1)
                        
                        confirmation_times.append({
                            "signature": sig,
                            "status": confirmation_status,
                            "blockTime": tx_data["blockTime"],
                            "confirmations": slots_to_confirm
                        })
            
            # Analyser les résultats
            if confirmation_times:
                successful_txs = [tx for tx in confirmation_times if tx["status"] == "success"]
                failed_txs = [tx for tx in confirmation_times if tx["status"] == "failed"]
                
                self.results["solana"]["confirmation_times"] = {
                    "successful": {
                        "count": len(successful_txs),
                        "average_confirmations": statistics.mean([tx["confirmations"] for tx in successful_txs]) if successful_txs else 0
                    },
                    "failed": {
                        "count": len(failed_txs),
                        "percentage": (len(failed_txs) / len(confirmation_times)) * 100 if confirmation_times else 0
                    },
                    "samples": len(confirmation_times)
                }
    
    async def analyze_mev_opportunities(self, rpc_url=None):
        """Analyse les potentielles opportunités MEV dans les blocs récents"""
        if rpc_url is None:
            rpc_url = self.solana_rpcs["mainnet"]
            
        print("Analyse des opportunités MEV potentielles...")
        
        # Récupérer le dernier bloc confirmé
        latest_slot = await self.get_latest_block(rpc_url)
        if latest_slot is None:
            print("Impossible de récupérer le dernier bloc")
            return
            
        # Récupérer et analyser des blocs récents
        mev_patterns = {
            "sandwich_attacks": 0,
            "arbitrage_transactions": 0,
            "multi_tx_patterns": 0,
            "high_priority_txs": 0
        }
        
        # Analyser 10 blocs récents
        for i in range(10):
            block = await self.get_block(rpc_url, latest_slot - i)
            if block and "transactions" in block:
                # Compter les transactions avec des fees élevés (potentiellement prioritaires)
                high_fee_txs = 0
                
                for tx in block["transactions"]:
                    if "meta" in tx and "fee" in tx["meta"]:
                        fee = tx["meta"]["fee"]
                        if fee > 10000:  # Seuil arbitraire pour les frais élevés
                            high_fee_txs += 1
                            
                            # Si la transaction contient plusieurs instructions, cela pourrait être de l'arbitrage
                            if "transaction" in tx and "message" in tx["transaction"]:
                                message = tx["transaction"]["message"]
                                if "instructions" in message and len(message["instructions"]) > 3:
                                    mev_patterns["arbitrage_transactions"] += 1
                
                mev_patterns["high_priority_txs"] += high_fee_txs
                
                # Identifier les motifs de sandwich (heuristique simplifiée)
                unique_accounts = set()
                
                for tx in block["transactions"]:
                    if "transaction" in tx and "message" in tx["transaction"]:
                        message = tx["transaction"]["message"]
                        if "accountKeys" in message:
                            for account in message["accountKeys"]:
                                unique_accounts.add(account)
                
                # Si un même compte apparaît dans plusieurs transactions du même bloc
                # c'est potentiellement un pattern MEV
                account_frequency = {}
                
                for tx in block["transactions"]:
                    if "transaction" in tx and "message" in tx["transaction"]:
                        message = tx["transaction"]["message"]
                        if "accountKeys" in message:
                            for account in message["accountKeys"]:
                                if account in account_frequency:
                                    account_frequency[account] += 1
                                else:
                                    account_frequency[account] = 1
                
                # Compter les comptes qui apparaissent dans plusieurs transactions
                multi_tx_accounts = sum(1 for count in account_frequency.values() if count > 1)
                if multi_tx_accounts > 0:
                    mev_patterns["multi_tx_patterns"] += 1
                    
                # Estimation simplifiée des sandwich attacks
                # (si une adresse apparaît au début et à la fin du bloc avec des transactions similaires)
                if len(block["transactions"]) > 5:
                    first_tx_accounts = set()
                    last_tx_accounts = set()
                    
                    if "transaction" in block["transactions"][0] and "message" in block["transactions"][0]["transaction"]:
                        first_tx_accounts = set(block["transactions"][0]["transaction"]["message"].get("accountKeys", []))
                        
                    if "transaction" in block["transactions"][-1] and "message" in block["transactions"][-1]["transaction"]:
                        last_tx_accounts = set(block["transactions"][-1]["transaction"]["message"].get("accountKeys", []))
                        
                    common_accounts = first_tx_accounts.intersection(last_tx_accounts)
                    if len(common_accounts) > 0:
                        mev_patterns["sandwich_attacks"] += 1
        
        self.results["solana"]["mev_analysis"] = mev_patterns
    
    async def simulate_priority_fees(self, rpc_url=None):
        """Simule l'impact des frais de priorité sur la vitesse de confirmation"""
        if rpc_url is None:
            rpc_url = self.solana_rpcs["mainnet"]
            
        print("Analyse de l'impact des frais de priorité...")
        
        # Structure pour stocker les résultats
        priority_fee_impact = {
            "low_fee": {"confirmations": [], "success_rate": 0},
            "medium_fee": {"confirmations": [], "success_rate": 0},
            "high_fee": {"confirmations": [], "success_rate": 0}
        }
        
        # Récupérer des transactions récentes avec différents niveaux de frais
        latest_slot = await self.get_latest_block(rpc_url)
        if latest_slot is None:
            print("Impossible de récupérer le dernier bloc")
            return
        
        # Récupérer des blocs récents et analyser les frais
        all_transactions = []
        
        for i in range(20):
            block = await self.get_block(rpc_url, latest_slot - i)
            if block and "transactions" in block:
                for tx in block["transactions"]:
                    if "meta" in tx and "fee" in tx["meta"] and "transaction" in tx and "signatures" in tx["transaction"]:
                        fee = tx["meta"]["fee"]
                        signature = tx["transaction"]["signatures"][0] if tx["transaction"]["signatures"] else None
                        if signature:
                            all_transactions.append({
                                "signature": signature,
                                "fee": fee
                            })
        
        # Trier les transactions par frais
        all_transactions.sort(key=lambda tx: tx["fee"])
        
        # Diviser en trois catégories: frais bas, moyens et élevés
        if all_transactions:
            fee_levels = []
            step = len(all_transactions) // 3
            
            low_fee_txs = all_transactions[:step]
            medium_fee_txs = all_transactions[step:2*step]
            high_fee_txs = all_transactions[2*step:]
            
            # Analyser un échantillon de chaque catégorie
            for category, txs, result_key in [
                ("Frais bas", low_fee_txs[:5], "low_fee"),
                ("Frais moyens", medium_fee_txs[:5], "medium_fee"),
                ("Frais élevés", high_fee_txs[:5], "high_fee")
            ]:
                successful = 0
                confirmations = []
                
                for tx_info in txs:
                    tx_data = await self.get_transaction(rpc_url, tx_info["signature"])
                    if tx_data:
                        if "meta" in tx_data and tx_data["meta"].get("err") is None:
                            successful += 1
                        
                        if "meta" in tx_data and "confirmations" in tx_data["meta"]:
                            confirmations.append(tx_data["meta"]["confirmations"])
                
                if txs:
                    priority_fee_impact[result_key]["success_rate"] = (successful / len(txs)) * 100
                    
                if confirmations:
                    priority_fee_impact[result_key]["confirmations"] = confirmations
                    priority_fee_impact[result_key]["avg_confirmations"] = statistics.mean(confirmations)
        
        self.results["solana"]["priority_fees"] = priority_fee_impact
    
    async def perform_full_benchmark(self, primary_rpc=None):
        """Exécute un benchmark complet des transactions Solana"""
        if primary_rpc is None:
            primary_rpc = self.solana_rpcs["mainnet"]
            
        # Mesurer le temps moyen entre les blocs
        await self.measure_block_time(primary_rpc)
        
        # Analyser la vitesse des transactions
        await self.analyze_transaction_speed(primary_rpc)
        
        # Analyser les opportunités MEV
        await self.analyze_mev_opportunities(primary_rpc)
        
        # Simuler l'impact des frais de priorité
        await self.simulate_priority_fees(primary_rpc)
        
        return self.results
    
    def save_results(self, filename="transaction_benchmark_results.json"):
        """Sauvegarde les résultats dans un fichier JSON"""
        with open(filename, 'w') as f:
            json.dump(self.results, f, indent=4)
        print(f"Résultats sauvegardés dans {filename}")
    
    def print_summary(self):
        """Affiche un résumé des résultats"""
        print("\n" + "="*50)
        print("RÉSUMÉ DU BENCHMARK DES TRANSACTIONS SOLANA")
        print("="*50)
        
        # Afficher les informations sur le temps de bloc
        if "block_time" in self.results["solana"] and isinstance(self.results["solana"]["block_time"], dict):
            block_time = self.results["solana"]["block_time"]
            print("\nTemps moyen entre les blocs:")
            print(f"- Moyenne: {block_time.get('average', 'N/A'):.3f} secondes")
            print(f"- Médiane: {block_time.get('median', 'N/A'):.3f} secondes")
            print(f"- Min: {block_time.get('min', 'N/A'):.3f} secondes")
            print(f"- Max: {block_time.get('max', 'N/A'):.3f} secondes")
            print(f"- Échantillon: {block_time.get('samples', 'N/A')} blocs")
            
        # Afficher les informations sur le temps de confirmation
        if "confirmation_times" in self.results["solana"]:
            confirmation = self.results["solana"]["confirmation_times"]
            print("\nTemps de confirmation des transactions:")
            
            if "successful" in confirmation:
                successful = confirmation["successful"]
                print(f"- Transactions réussies: {successful.get('count', 0)}")
                print(f"- Confirmations moyennes: {successful.get('average_confirmations', 'N/A')}")
                
            if "failed" in confirmation:
                failed = confirmation["failed"]
                print(f"- Transactions échouées: {failed.get('count', 0)} ({failed.get('percentage', 0):.1f}%)")
                
            print(f"- Échantillon total: {confirmation.get('samples', 0)} transactions")
            
        # Afficher les informations sur les opportunités MEV
        if "mev_analysis" in self.results["solana"]:
            mev = self.results["solana"]["mev_analysis"]
            print("\nAnalyse des opportunités MEV potentielles (sur les 10 derniers blocs):")
            print(f"- Attaques sandwich potentielles: {mev.get('sandwich_attacks', 0)}")
            print(f"- Transactions d'arbitrage potentielles: {mev.get('arbitrage_transactions', 0)}")
            print(f"- Patterns multi-transactions: {mev.get('multi_tx_patterns', 0)}")
            print(f"- Transactions à haute priorité: {mev.get('high_priority_txs', 0)}")
            
        # Afficher les informations sur l'impact des frais de priorité
        if "priority_fees" in self.results["solana"]:
            fees = self.results["solana"]["priority_fees"]
            print("\nImpact des frais de priorité:")
            
            for level, label in [
                ("low_fee", "Frais bas"),
                ("medium_fee", "Frais moyens"),
                ("high_fee", "Frais élevés")
            ]:
                if level in fees:
                    fee_data = fees[level]
                    success_rate = fee_data.get("success_rate", 0)
                    avg_confirmations = fee_data.get("avg_confirmations", "N/A")
                    
                    if isinstance(avg_confirmations, (int, float)):
                        confirm_str = f"{avg_confirmations:.1f} confirmations"
                    else:
                        confirm_str = "N/A"
                        
                    print(f"- {label}: {success_rate:.1f}% de succès, {confirm_str}")
            
        print("\nRecommandations pour le sniping:")
        print("- Idéalement, soumettre les transactions dans les {:.1f} secondes après un nouveau bloc".format(
            self.results["solana"].get("block_time", {}).get("average", 0) * 0.5
        ))
        print("- Utiliser des frais de priorité pour augmenter les chances d'inclusion rapide")
        print("- Monitorer les blocks en temps réel pour détecter les opportunités MEV")
        print("="*50)

async def main():
    benchmark = TransactionBenchmark()
    await benchmark.perform_full_benchmark()
    benchmark.save_results("benchmarking/transaction_benchmark_results.json")
    benchmark.print_summary()

if __name__ == "__main__":
    asyncio.run(main()) 