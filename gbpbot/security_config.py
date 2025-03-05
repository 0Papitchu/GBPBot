import os
import ipaddress
import secrets
import hashlib
import time
from functools import wraps
from flask import request, jsonify
from dotenv import load_dotenv
from loguru import logger

# Charger les variables d'environnement depuis le fichier .env
load_dotenv()

# Configuration de sécurité
class SecurityConfig:
    def __init__(self):
        # Clé API (par défaut si non définie dans les variables d'environnement)
        self.api_key = os.getenv("GBPBOT_API_KEY")
        
        # Générer une clé API sécurisée si elle n'existe pas
        if not self.api_key:
            self.api_key = self._generate_secure_api_key()
            logger.warning(f"Aucune clé API trouvée dans les variables d'environnement. Une clé temporaire a été générée: {self.api_key}")
            logger.warning("Cette clé sera perdue au redémarrage. Ajoutez-la à votre fichier .env avec GBPBOT_API_KEY=votre_clé")
        
        # Liste des IPs autorisées (format: "192.168.1.1,10.0.0.0/24")
        ip_whitelist_str = os.getenv("GBPBOT_IP_WHITELIST", "127.0.0.1,::1")
        self.ip_whitelist = self._parse_ip_whitelist(ip_whitelist_str)
        
        # Activer/désactiver la vérification d'IP
        self.enable_ip_check = os.getenv("GBPBOT_ENABLE_IP_CHECK", "true").lower() == "true"
        
        # Configuration SSL/TLS
        self.ssl_cert_path = os.getenv("GBPBOT_SSL_CERT", "")
        self.ssl_key_path = os.getenv("GBPBOT_SSL_KEY", "")
        self.use_https = bool(self.ssl_cert_path and self.ssl_key_path)
        
        # Si HTTPS est activé, vérifier que les fichiers existent
        if self.use_https:
            if not os.path.exists(self.ssl_cert_path):
                logger.error(f"Le certificat SSL spécifié n'existe pas: {self.ssl_cert_path}")
                self.use_https = False
            if not os.path.exists(self.ssl_key_path):
                logger.error(f"La clé SSL spécifiée n'existe pas: {self.ssl_key_path}")
                self.use_https = False
        
        # Journalisation des requêtes
        self.log_requests = os.getenv("GBPBOT_LOG_REQUESTS", "true").lower() == "true"
        
        # Niveau de journalisation
        self.log_level = os.getenv("GBPBOT_LOG_LEVEL", "INFO")
        
        # Limites de taux de requêtes (rate limiting)
        self.rate_limit_default = os.getenv("GBPBOT_RATE_LIMIT_DEFAULT", "60 per minute")
        self.rate_limit_auth = os.getenv("GBPBOT_RATE_LIMIT_AUTH", "10 per minute")
        
        # Délai d'expiration des requêtes (en secondes)
        self.request_timeout = int(os.getenv("GBPBOT_REQUEST_TIMEOUT", "30"))
        
        # Protection contre les attaques par force brute
        self.max_failed_attempts = int(os.getenv("GBPBOT_MAX_FAILED_ATTEMPTS", "5"))
        self.failed_attempts = {}
        self.lockout_time = int(os.getenv("GBPBOT_LOCKOUT_TIME", "300"))  # 5 minutes
        
        logger.info(f"Configuration de sécurité chargée")
        logger.info(f"Vérification d'IP: {'Activée' if self.enable_ip_check else 'Désactivée'}")
        logger.info(f"HTTPS: {'Activé' if self.use_https else 'Désactivé'}")
        logger.info(f"Journalisation des requêtes: {'Activée' if self.log_requests else 'Désactivée'}")
    
    def _generate_secure_api_key(self):
        """Générer une clé API sécurisée"""
        return secrets.token_hex(32)
    
    def _parse_ip_whitelist(self, ip_whitelist_str):
        """Parse la liste des IPs autorisées depuis une chaîne de caractères"""
        ip_whitelist = []
        for ip_str in ip_whitelist_str.split(','):
            ip_str = ip_str.strip()
            if not ip_str:
                continue
                
            try:
                # Vérifier si c'est un réseau (CIDR) ou une IP simple
                if '/' in ip_str:
                    ip_network = ipaddress.ip_network(ip_str, strict=False)
                    ip_whitelist.append(ip_network)
                else:
                    ip_address = ipaddress.ip_address(ip_str)
                    ip_whitelist.append(ip_address)
            except ValueError as e:
                logger.error(f"IP invalide dans la liste blanche: {ip_str} - {str(e)}")
        
        return ip_whitelist
    
    def is_ip_allowed(self, ip_str):
        """Vérifier si une IP est autorisée"""
        if not self.enable_ip_check:
            return True
            
        if not ip_str:
            return False
            
        try:
            client_ip = ipaddress.ip_address(ip_str)
            
            # Vérifier si l'IP est dans la liste blanche
            for ip in self.ip_whitelist:
                if isinstance(ip, ipaddress.IPv4Network) or isinstance(ip, ipaddress.IPv6Network):
                    if client_ip in ip:
                        return True
                elif ip == client_ip:
                    return True
                    
            return False
        except ValueError:
            logger.error(f"Format d'IP invalide: {ip_str}")
            return False
    
    def get_ssl_context(self):
        """Obtenir le contexte SSL pour Flask"""
        if self.use_https:
            return (self.ssl_cert_path, self.ssl_key_path)
        return None
    
    def check_failed_attempts(self, ip):
        """Vérifier si une IP a dépassé le nombre maximum de tentatives échouées"""
        if ip in self.failed_attempts:
            attempts, timestamp = self.failed_attempts[ip]
            
            # Vérifier si le délai de verrouillage est passé
            if attempts >= self.max_failed_attempts:
                if time.time() - timestamp < self.lockout_time:
                    return False  # IP verrouillée
                else:
                    # Réinitialiser le compteur après le délai de verrouillage
                    self.failed_attempts[ip] = (0, time.time())
        
        return True
    
    def record_failed_attempt(self, ip):
        """Enregistrer une tentative d'authentification échouée"""
        if ip in self.failed_attempts:
            attempts, _ = self.failed_attempts[ip]
            self.failed_attempts[ip] = (attempts + 1, time.time())
        else:
            self.failed_attempts[ip] = (1, time.time())
    
    def reset_failed_attempts(self, ip):
        """Réinitialiser le compteur de tentatives échouées pour une IP"""
        if ip in self.failed_attempts:
            self.failed_attempts[ip] = (0, time.time())

def require_auth(security_config):
    """Décorateur pour exiger l'authentification API"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Obtenir l'IP du client
            client_ip = request.remote_addr
            
            # Vérifier si l'IP est autorisée
            if security_config.enable_ip_check and not security_config.is_ip_allowed(client_ip):
                logger.warning(f"Tentative d'accès depuis une IP non autorisée: {client_ip}")
                return jsonify({"error": "Accès non autorisé"}), 403
            
            # Vérifier si l'IP est verrouillée en raison de trop nombreuses tentatives échouées
            if not security_config.check_failed_attempts(client_ip):
                logger.warning(f"IP verrouillée en raison de trop nombreuses tentatives échouées: {client_ip}")
                return jsonify({"error": "Trop de tentatives échouées. Réessayez plus tard."}), 429
            
            # Vérifier la clé API
            api_key = request.headers.get('x-api-key')
            if not api_key or api_key != security_config.api_key:
                security_config.record_failed_attempt(client_ip)
                logger.warning(f"Tentative d'accès avec une clé API invalide depuis: {client_ip}")
                return jsonify({"error": "Authentification requise"}), 401
            
            # Réinitialiser le compteur de tentatives échouées en cas de succès
            security_config.reset_failed_attempts(client_ip)
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# Exemple d'utilisation dans un fichier .env
"""
# Fichier .env
GBPBOT_API_KEY=votre_clé_api_très_sécurisée
GBPBOT_IP_WHITELIST=127.0.0.1,192.168.1.0/24,10.0.0.5
GBPBOT_ENABLE_IP_CHECK=true
GBPBOT_SSL_CERT=/chemin/vers/certificat.pem
GBPBOT_SSL_KEY=/chemin/vers/clé.pem
GBPBOT_LOG_REQUESTS=true
GBPBOT_LOG_LEVEL=INFO
"""

# Créer une instance de la configuration de sécurité
security_config = SecurityConfig() 