#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script pour générer un certificat SSL auto-signé pour les tests HTTPS.
Ce certificat ne doit être utilisé que pour les tests et le développement,
pas pour la production.
"""

import os
import sys
import argparse
import datetime
import ipaddress
from cryptography import x509
from cryptography.x509.oid import NameOID, ExtendedKeyUsageOID
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
from loguru import logger

# Configurer le logger
logger.remove()
logger.add(sys.stderr, level="INFO")
logger.add("ssl_cert_generation.log", rotation="10 MB", level="DEBUG")

def generate_ssl_cert(output_dir=".", common_name="localhost", days_valid=365, key_size=4096):
    """
    Générer un certificat SSL auto-signé.
    
    Args:
        output_dir: Répertoire de sortie pour les fichiers de certificat
        common_name: Nom commun pour le certificat (généralement le nom d'hôte)
        days_valid: Nombre de jours de validité du certificat
        key_size: Taille de la clé RSA en bits (4096 recommandé pour la sécurité)
    
    Returns:
        tuple: Chemins des fichiers de certificat et de clé privée
    """
    logger.info(f"Génération d'un certificat SSL auto-signé pour '{common_name}'")
    logger.info(f"Taille de la clé: {key_size} bits, Validité: {days_valid} jours")
    
    # Créer le répertoire de sortie s'il n'existe pas
    os.makedirs(output_dir, exist_ok=True)
    
    # Générer une clé privée RSA avec une taille de clé plus sécurisée
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=key_size,
    )
    
    # Créer un certificat auto-signé
    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME, "FR"),
        x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "Ile-de-France"),
        x509.NameAttribute(NameOID.LOCALITY_NAME, "Paris"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "GBPBot Development"),
        x509.NameAttribute(NameOID.COMMON_NAME, common_name),
    ])
    
    # Ajouter des noms alternatifs (SANs)
    san_list = []
    
    # Ajouter le nom commun et localhost comme noms DNS
    san_list.append(x509.DNSName(common_name))
    if common_name != "localhost":
        san_list.append(x509.DNSName("localhost"))
    
    # Ajouter les adresses IP
    try:
        # Vérifier si common_name est une adresse IP
        ip = ipaddress.ip_address(common_name)
        san_list.append(x509.IPAddress(ip))
    except ValueError:
        # Si ce n'est pas une adresse IP, c'est probablement un nom d'hôte
        pass
    
    # Ajouter 127.0.0.1 comme adresse IP
    san_list.append(x509.IPAddress(ipaddress.ip_address("127.0.0.1")))
    
    # Créer le certificat avec des algorithmes plus sécurisés
    cert = x509.CertificateBuilder().subject_name(
        subject
    ).issuer_name(
        issuer
    ).public_key(
        private_key.public_key()
    ).serial_number(
        x509.random_serial_number()
    ).not_valid_before(
        datetime.datetime.utcnow()
    ).not_valid_after(
        datetime.datetime.utcnow() + datetime.timedelta(days=days_valid)
    ).add_extension(
        x509.SubjectAlternativeName(san_list),
        critical=False,
    ).add_extension(
        x509.BasicConstraints(ca=False, path_length=None),
        critical=True,
    ).add_extension(
        x509.KeyUsage(
            digital_signature=True,
            content_commitment=False,
            key_encipherment=True,
            data_encipherment=False,
            key_agreement=False,
            key_cert_sign=False,
            crl_sign=False,
            encipher_only=False,
            decipher_only=False
        ),
        critical=True
    ).add_extension(
        x509.ExtendedKeyUsage([
            ExtendedKeyUsageOID.SERVER_AUTH,
            ExtendedKeyUsageOID.CLIENT_AUTH
        ]),
        critical=False
    ).sign(private_key, hashes.SHA384())  # Utilisation de SHA-384 pour plus de sécurité
    
    # Éviter les noms de fichiers prévisibles pour éviter les attaques ciblées
    timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    cert_filename = f"{common_name}_{timestamp}.crt"
    key_filename = f"{common_name}_{timestamp}.key"
    
    cert_path = os.path.join(output_dir, cert_filename)
    key_path = os.path.join(output_dir, key_filename)
    
    # Écrire le certificat dans un fichier
    with open(cert_path, "wb") as f:
        f.write(cert.public_bytes(serialization.Encoding.PEM))
    
    # Définir des permissions restrictives sur le fichier de clé privée
    # Écrire la clé privée dans un fichier avec un format sécurisé
    with open(key_path, "wb") as f:
        f.write(private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        ))
    
    # Restreindre les permissions du fichier de clé (fonctionne uniquement sur Unix/Linux)
    try:
        if os.name != 'nt':  # Skip on Windows
            os.chmod(key_path, 0o600)  # Lecture/écriture uniquement pour le propriétaire
    except Exception as e:
        logger.warning(f"Impossible de définir les permissions sur le fichier de clé: {e}")
    
    logger.info(f"Certificat généré: {cert_path}")
    logger.info(f"Clé privée générée: {key_path}")
    
    # Afficher les instructions pour configurer le certificat
    logger.info("\nPour utiliser ce certificat avec GBPBot, ajoutez les lignes suivantes à votre fichier .env:")
    logger.info(f"GBPBOT_SSL_CERT={cert_path}")
    logger.info(f"GBPBOT_SSL_KEY={key_path}")
    logger.info("\nATTENTION: Ce certificat est auto-signé et destiné uniquement aux tests.")
    logger.info("Pour la production, utilisez un certificat signé par une autorité de certification reconnue.")
    
    return cert_path, key_path

def main():
    """Fonction principale."""
    parser = argparse.ArgumentParser(description="Générer un certificat SSL auto-signé pour les tests HTTPS")
    parser.add_argument("--output-dir", default=".", help="Répertoire de sortie pour les fichiers de certificat")
    parser.add_argument("--common-name", default="localhost", help="Nom commun pour le certificat (généralement le nom d'hôte)")
    parser.add_argument("--days", type=int, default=365, help="Nombre de jours de validité du certificat")
    parser.add_argument("--key-size", type=int, default=4096, help="Taille de la clé RSA en bits (4096 recommandé)")
    args = parser.parse_args()
    
    generate_ssl_cert(
        output_dir=args.output_dir,
        common_name=args.common_name,
        days_valid=args.days,
        key_size=args.key_size
    )

if __name__ == "__main__":
    main() 