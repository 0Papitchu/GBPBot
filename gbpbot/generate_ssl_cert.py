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
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
from loguru import logger

# Configurer le logger
logger.remove()
logger.add(sys.stderr, level="INFO")
logger.add("ssl_cert_generation.log", rotation="10 MB", level="DEBUG")

def generate_ssl_cert(output_dir=".", common_name="localhost", days_valid=365, key_size=2048):
    """
    Générer un certificat SSL auto-signé.
    
    Args:
        output_dir: Répertoire de sortie pour les fichiers de certificat
        common_name: Nom commun pour le certificat (généralement le nom d'hôte)
        days_valid: Nombre de jours de validité du certificat
        key_size: Taille de la clé RSA en bits
    
    Returns:
        tuple: Chemins des fichiers de certificat et de clé privée
    """
    logger.info(f"Génération d'un certificat SSL auto-signé pour '{common_name}'")
    logger.info(f"Taille de la clé: {key_size} bits, Validité: {days_valid} jours")
    
    # Créer le répertoire de sortie s'il n'existe pas
    os.makedirs(output_dir, exist_ok=True)
    
    # Générer une clé privée RSA
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
    san_list = [x509.DNSName(common_name)]
    
    # Ajouter localhost et 127.0.0.1 comme SANs
    if common_name != "localhost":
        san_list.append(x509.DNSName("localhost"))
    
    try:
        # Vérifier si common_name est une adresse IP
        ipaddress.ip_address(common_name)
        san_list.append(x509.IPAddress(ipaddress.ip_address(common_name)))
    except ValueError:
        # Si ce n'est pas une adresse IP, c'est probablement un nom d'hôte
        pass
    
    # Ajouter 127.0.0.1 comme SAN
    san_list.append(x509.IPAddress(ipaddress.ip_address("127.0.0.1")))
    
    # Créer le certificat
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
    ).sign(private_key, hashes.SHA256())
    
    # Chemins des fichiers de sortie
    cert_path = os.path.join(output_dir, f"{common_name}.crt")
    key_path = os.path.join(output_dir, f"{common_name}.key")
    
    # Écrire le certificat dans un fichier
    with open(cert_path, "wb") as f:
        f.write(cert.public_bytes(serialization.Encoding.PEM))
    
    # Écrire la clé privée dans un fichier
    with open(key_path, "wb") as f:
        f.write(private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        ))
    
    logger.info(f"Certificat généré: {cert_path}")
    logger.info(f"Clé privée générée: {key_path}")
    
    # Afficher les instructions pour configurer le certificat
    logger.info("\nPour utiliser ce certificat avec GBPBot, ajoutez les lignes suivantes à votre fichier .env:")
    logger.info(f"GBPBOT_SSL_CERT={cert_path}")
    logger.info(f"GBPBOT_SSL_KEY={key_path}")
    
    return cert_path, key_path

def main():
    """Fonction principale."""
    parser = argparse.ArgumentParser(description="Générer un certificat SSL auto-signé pour les tests HTTPS")
    parser.add_argument("--output-dir", default=".", help="Répertoire de sortie pour les fichiers de certificat")
    parser.add_argument("--common-name", default="localhost", help="Nom commun pour le certificat (généralement le nom d'hôte)")
    parser.add_argument("--days", type=int, default=365, help="Nombre de jours de validité du certificat")
    parser.add_argument("--key-size", type=int, default=2048, help="Taille de la clé RSA en bits")
    args = parser.parse_args()
    
    generate_ssl_cert(
        output_dir=args.output_dir,
        common_name=args.common_name,
        days_valid=args.days,
        key_size=args.key_size
    )

if __name__ == "__main__":
    main() 