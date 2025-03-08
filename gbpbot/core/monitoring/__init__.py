#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Package de monitoring unifié pour GBPBot
========================================

Ce package fournit un système unifié pour la surveillance des performances
et des ressources dans GBPBot, remplaçant les implémentations disparates
précédentes par une architecture cohérente et extensible.
"""

from .base_monitor import BaseMonitor, MonitoringException, MetricValue, MetricDict, CallbackType
from .system_monitor import SystemMonitor, get_system_monitor
from .compatibility import (
    ResourceMonitorCompat, PerformanceMonitorCompat,
    get_resource_monitor, get_performance_monitor
)
# Les imports seront ajoutés au fur et à mesure que nous implémentons les classes

__all__ = [
    'BaseMonitor',
    'MonitoringException',
    'MetricValue',
    'MetricDict',
    'CallbackType',
    'SystemMonitor',
    'get_system_monitor',
    # Les autres classes seront ajoutées ici
] 