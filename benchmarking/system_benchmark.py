import time
import json
import os
import platform
import psutil
import subprocess
import statistics
from datetime import datetime

# Import conditionnel pour speedtest-cli
try:
    import speedtest
    SPEEDTEST_AVAILABLE = True
except ImportError:
    print("Module speedtest-cli non disponible. Les tests de vitesse Internet seront désactivés.")
    SPEEDTEST_AVAILABLE = False

class SystemBenchmark:
    def __init__(self):
        self.results = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "system": {},
            "cpu": {},
            "memory": {},
            "disk": {},
            "network": {}
        }
        
    def benchmark_system_info(self):
        """Collecte des informations générales sur le système"""
        print("Benchmark des informations système...")
        
        system_info = {
            "platform": platform.system(),
            "platform_release": platform.release(),
            "platform_version": platform.version(),
            "architecture": platform.machine(),
            "processor": platform.processor(),
            "hostname": platform.node()
        }
        
        # Informations sur la mémoire
        memory = psutil.virtual_memory()
        system_info["ram_total_gb"] = round(memory.total / (1024**3), 2)
        
        # Informations sur le CPU
        system_info["cpu_cores_physical"] = psutil.cpu_count(logical=False)
        system_info["cpu_cores_logical"] = psutil.cpu_count(logical=True)
        
        # Informations sur le disque
        disk = psutil.disk_usage('/')
        system_info["disk_total_gb"] = round(disk.total / (1024**3), 2)
        system_info["disk_free_gb"] = round(disk.free / (1024**3), 2)
        
        self.results["system"] = system_info
        return system_info
        
    def benchmark_cpu(self, duration=5):
        """Benchmark des performances CPU"""
        print(f"Benchmark CPU en cours (durée: {duration}s)...")
        
        # Collecter l'utilisation CPU
        cpu_usage = []
        start_time = time.time()
        
        while time.time() - start_time < duration:
            cpu_percent = psutil.cpu_percent(interval=0.5)
            cpu_usage.append(cpu_percent)
            
        # Calcul des fréquences
        cpu_freq = psutil.cpu_freq()
        
        # Résultats
        cpu_results = {
            "current_usage_percent": psutil.cpu_percent(interval=1),
            "avg_usage_percent": statistics.mean(cpu_usage) if cpu_usage else 0,
            "max_usage_percent": max(cpu_usage) if cpu_usage else 0,
            "min_usage_percent": min(cpu_usage) if cpu_usage else 0
        }
        
        if cpu_freq:
            cpu_results["frequency_current_mhz"] = cpu_freq.current
            if hasattr(cpu_freq, 'min') and cpu_freq.min:
                cpu_results["frequency_min_mhz"] = cpu_freq.min
            if hasattr(cpu_freq, 'max') and cpu_freq.max:
                cpu_results["frequency_max_mhz"] = cpu_freq.max
                
        # Test de charge CPU simple
        start_time = time.time()
        iterations = 0
        
        # Effectuer un calcul intensif pendant 2 secondes
        while time.time() - start_time < 2:
            for i in range(1000000):
                iterations += 1
                _ = i ** 2
                
        cpu_results["calculation_score"] = iterations
        
        self.results["cpu"] = cpu_results
        return cpu_results
        
    def benchmark_memory(self):
        """Benchmark des performances mémoire"""
        print("Benchmark mémoire en cours...")
        
        # Informations sur la mémoire
        memory = psutil.virtual_memory()
        swap = psutil.swap_memory()
        
        memory_results = {
            "total_gb": round(memory.total / (1024**3), 2),
            "available_gb": round(memory.available / (1024**3), 2),
            "used_gb": round(memory.used / (1024**3), 2),
            "percent_used": memory.percent,
            "swap_total_gb": round(swap.total / (1024**3), 2),
            "swap_used_gb": round(swap.used / (1024**3), 2),
            "swap_percent_used": swap.percent
        }
        
        # Test simple de vitesse d'allocation/désallocation
        start_time = time.time()
        iterations = 0
        
        # Allouer et désallouer de la mémoire pendant 2 secondes
        while time.time() - start_time < 2:
            for i in range(100):
                large_list = [0] * 10000
                iterations += 1
                
        memory_results["allocation_score"] = iterations
        
        self.results["memory"] = memory_results
        return memory_results
        
    def benchmark_disk(self, test_file_size_mb=100):
        """Benchmark des performances disque"""
        print("Benchmark disque en cours...")
        
        # Informations générales sur le disque
        disk = psutil.disk_usage('/')
        disk_io = psutil.disk_io_counters(perdisk=False)
        
        disk_results = {
            "total_gb": round(disk.total / (1024**3), 2),
            "used_gb": round(disk.used / (1024**3), 2),
            "free_gb": round(disk.free / (1024**3), 2),
            "percent_used": disk.percent
        }
        
        if disk_io:
            disk_results["read_count"] = disk_io.read_count
            disk_results["write_count"] = disk_io.write_count
            disk_results["read_bytes"] = disk_io.read_bytes
            disk_results["write_bytes"] = disk_io.write_bytes
            
        # Test de lecture/écriture
        test_file = "benchmark_disk_test.dat"
        test_size = test_file_size_mb * 1024 * 1024  # Convertir en octets
        
        # Écriture
        write_speeds = []
        try:
            for i in range(3):  # Effectuer 3 tests
                data = b"0" * 1024  # 1KB de données
                start_time = time.time()
                
                with open(test_file, 'wb') as f:
                    bytes_written = 0
                    while bytes_written < test_size:
                        f.write(data)
                        bytes_written += len(data)
                        
                end_time = time.time()
                duration = end_time - start_time
                write_speed = (bytes_written / 1024 / 1024) / duration if duration > 0 else 0  # MB/s
                write_speeds.append(write_speed)
                
            # Lecture
            read_speeds = []
            
            for i in range(3):  # Effectuer 3 tests
                start_time = time.time()
                
                with open(test_file, 'rb') as f:
                    while f.read(8192):
                        pass
                        
                end_time = time.time()
                duration = end_time - start_time
                read_speed = (test_size / 1024 / 1024) / duration if duration > 0 else 0  # MB/s
                read_speeds.append(read_speed)
                
            # Supprimer le fichier de test
            if os.path.exists(test_file):
                os.remove(test_file)
                
            # Calculer les moyennes
            if write_speeds:
                disk_results["write_speed_mb_per_sec"] = statistics.mean(write_speeds)
                
            if read_speeds:
                disk_results["read_speed_mb_per_sec"] = statistics.mean(read_speeds)
                
        except Exception as e:
            disk_results["error"] = f"Erreur lors du test de disque: {str(e)}"
            
        self.results["disk"] = disk_results
        return disk_results
        
    def benchmark_network(self):
        """Benchmark des performances réseau"""
        print("Benchmark réseau en cours...")
        
        network_results = {}
        
        # Collecter les informations sur les interfaces réseau
        net_io = psutil.net_io_counters(pernic=True)
        network_results["interfaces"] = {}
        
        for interface, stats in net_io.items():
            network_results["interfaces"][interface] = {
                "bytes_sent": stats.bytes_sent,
                "bytes_recv": stats.bytes_recv,
                "packets_sent": stats.packets_sent,
                "packets_recv": stats.packets_recv
            }
            
        # Test de vitesse Internet avec speedtest-cli si disponible
        if SPEEDTEST_AVAILABLE:
            try:
                print("Test de vitesse Internet en cours...")
                st = speedtest.Speedtest()
                st.get_best_server()
                
                # Test de download
                download_speed = st.download() / 1024 / 1024  # Mbit/s
                network_results["download_speed_mbps"] = round(download_speed, 2)
                
                # Test de upload
                upload_speed = st.upload() / 1024 / 1024  # Mbit/s
                network_results["upload_speed_mbps"] = round(upload_speed, 2)
                
                # Ping
                ping = st.results.ping
                network_results["ping_ms"] = round(ping, 2)
                
                # Informations sur le serveur
                server = st.get_best_server()
                network_results["speedtest_server"] = {
                    "host": server["host"],
                    "location": f"{server['name']}, {server['country']}",
                    "distance": round(server["d"], 2)
                }
            except Exception as e:
                network_results["speedtest_error"] = f"Erreur lors du test de vitesse: {str(e)}"
        else:
            network_results["speedtest"] = "Non disponible"
            
        # Test de latence vers des hôtes populaires
        hosts = ["google.com", "amazon.com", "cloudflare.com", "1.1.1.1"]
        network_results["latency_ms"] = {}
        
        for host in hosts:
            try:
                # Utiliser ping pour mesurer la latence
                if platform.system().lower() == "windows":
                    cmd = ["ping", "-n", "4", host]
                else:
                    cmd = ["ping", "-c", "4", host]
                    
                output = subprocess.check_output(cmd).decode()
                
                # Extraire le temps moyen
                if platform.system().lower() == "windows":
                    avg_line = [line for line in output.split('\n') if "Moyenne" in line or "Average" in line]
                    if avg_line:
                        avg_time = avg_line[0].split("=")[-1].strip().replace("ms", "").strip()
                        network_results["latency_ms"][host] = float(avg_time)
                else:
                    avg_line = [line for line in output.split('\n') if "avg" in line]
                    if avg_line:
                        avg_time = avg_line[0].split("/")[4]
                        network_results["latency_ms"][host] = float(avg_time)
            except Exception as e:
                network_results["latency_ms"][host] = f"Erreur: {str(e)}"
                
        self.results["network"] = network_results
        return network_results
        
    def run_all_benchmarks(self, disk_test_size_mb=50):
        """Exécute tous les benchmarks"""
        self.benchmark_system_info()
        self.benchmark_cpu()
        self.benchmark_memory()
        self.benchmark_disk(disk_test_size_mb)
        self.benchmark_network()
        
        return self.results
        
    def save_results(self, filename="system_benchmark_results.json"):
        """Sauvegarde les résultats dans un fichier JSON"""
        with open(filename, 'w') as f:
            json.dump(self.results, f, indent=4)
        print(f"Résultats sauvegardés dans {filename}")
        
    def print_summary(self):
        """Affiche un résumé des résultats"""
        print("\n" + "="*50)
        print("RÉSUMÉ DU BENCHMARK SYSTÈME")
        print("="*50)
        
        # Informations système
        if "system" in self.results:
            sys_info = self.results["system"]
            print("\nInformations système:")
            print(f"- Plateforme: {sys_info.get('platform')} {sys_info.get('platform_release')}")
            print(f"- Architecture: {sys_info.get('architecture')}")
            print(f"- Processeur: {sys_info.get('processor')}")
            print(f"- RAM totale: {sys_info.get('ram_total_gb')} GB")
            print(f"- Cœurs CPU: {sys_info.get('cpu_cores_physical')} physiques, {sys_info.get('cpu_cores_logical')} logiques")
            
        # Résultats CPU
        if "cpu" in self.results:
            cpu = self.results["cpu"]
            print("\nPerformances CPU:")
            print(f"- Utilisation actuelle: {cpu.get('current_usage_percent')}%")
            print(f"- Fréquence actuelle: {cpu.get('frequency_current_mhz')} MHz")
            print(f"- Score de calcul: {cpu.get('calculation_score')}")
            
        # Résultats mémoire
        if "memory" in self.results:
            mem = self.results["memory"]
            print("\nPerformances mémoire:")
            print(f"- RAM disponible: {mem.get('available_gb')} GB / {mem.get('total_gb')} GB")
            print(f"- Utilisation RAM: {mem.get('percent_used')}%")
            print(f"- Score d'allocation: {mem.get('allocation_score')}")
            
        # Résultats disque
        if "disk" in self.results:
            disk = self.results["disk"]
            print("\nPerformances disque:")
            print(f"- Espace disponible: {disk.get('free_gb')} GB / {disk.get('total_gb')} GB")
            print(f"- Vitesse d'écriture: {disk.get('write_speed_mb_per_sec', 'N/A')} MB/s")
            print(f"- Vitesse de lecture: {disk.get('read_speed_mb_per_sec', 'N/A')} MB/s")
            
        # Résultats réseau
        if "network" in self.results:
            net = self.results["network"]
            print("\nPerformances réseau:")
            
            if "download_speed_mbps" in net:
                print(f"- Vitesse de téléchargement: {net.get('download_speed_mbps')} Mbps")
                print(f"- Vitesse d'upload: {net.get('upload_speed_mbps')} Mbps")
                print(f"- Ping: {net.get('ping_ms')} ms")
            else:
                print("- Test de vitesse Internet non disponible")
                
            if "latency_ms" in net:
                print("\nLatence vers des hôtes populaires:")
                for host, latency in net["latency_ms"].items():
                    print(f"- {host}: {latency} ms")
                    
        print("\nRecommandation pour GBPBot:")
        
        # Évaluer si le système est adapté à GBPBot
        system_score = 0
        recommendations = []
        
        # Évaluer CPU
        if "cpu" in self.results:
            cpu_cores = self.results["system"].get("cpu_cores_logical", 0)
            if cpu_cores >= 8:
                system_score += 3
            elif cpu_cores >= 4:
                system_score += 2
                recommendations.append("Limiter le nombre de stratégies exécutées simultanément")
            else:
                system_score += 1
                recommendations.append("Activer le mode d'économie de ressources CPU")
                
        # Évaluer RAM
        if "memory" in self.results:
            ram_gb = self.results["system"].get("ram_total_gb", 0)
            if ram_gb >= 16:
                system_score += 3
            elif ram_gb >= 8:
                system_score += 2
                recommendations.append("Réduire la taille du cache en mémoire")
            else:
                system_score += 1
                recommendations.append("Désactiver certaines fonctionnalités consommatrices de mémoire")
                
        # Évaluer disque
        if "disk" in self.results:
            write_speed = self.results["disk"].get("write_speed_mb_per_sec", 0)
            if write_speed >= 100:
                system_score += 3
            elif write_speed >= 50:
                system_score += 2
                recommendations.append("Réduire la fréquence des sauvegardes sur disque")
            else:
                system_score += 1
                recommendations.append("Utiliser un SSD pour le stockage des données")
                
        # Évaluer réseau
        if "network" in self.results and "download_speed_mbps" in self.results["network"]:
            download = self.results["network"].get("download_speed_mbps", 0)
            if download >= 100:
                system_score += 3
            elif download >= 50:
                system_score += 2
                recommendations.append("Réduire le nombre de connexions parallèles")
            else:
                system_score += 1
                recommendations.append("Activer le mode d'économie de bande passante")
                
        # Afficher le score et les recommandations
        max_score = 12
        score_percent = (system_score / max_score) * 100
        
        print(f"\nScore de compatibilité GBPBot: {system_score}/{max_score} ({score_percent:.1f}%)")
        
        if score_percent >= 75:
            print("Votre système est bien adapté pour exécuter GBPBot avec toutes les fonctionnalités.")
        elif score_percent >= 50:
            print("Votre système peut exécuter GBPBot avec quelques ajustements.")
        else:
            print("Votre système nécessite des ajustements importants pour exécuter GBPBot efficacement.")
            
        if recommendations:
            print("\nRecommandations spécifiques:")
            for rec in recommendations:
                print(f"- {rec}")
                
        print("="*50)

def main():
    benchmark = SystemBenchmark()
    benchmark.run_all_benchmarks()
    benchmark.save_results("benchmarking/system_benchmark_results.json")
    benchmark.print_summary()

if __name__ == "__main__":
    main() 