import streamlit as st
from collections import defaultdict
from typing import Any, Callable

class SessionStateManager:
    """
    Gestion centralisée du session_state Streamlit
    """
    
    def __init__(self, namespace: str = ""):
        """
        namespace : préfixe appliqué à toutes les clés pour éviter les collisions
        """
        self.ns = f"{namespace}:" if namespace else ""

    def _full_key(self, key: str) -> str:
        """Ajoute le namespace au nom de la clé"""
        return f"{self.ns}{key}"

    def init(self, key: str, default: Any):
        """
        Initialise une clé avec une valeur par défaut si elle n'existe pas déjà.
        """
        fk = self._full_key(key)
        if fk not in st.session_state:
            # On copie les conteneurs mutables pour éviter les effets de bord
            if isinstance(default, (dict, list, set, defaultdict)):
                st.session_state[fk] = default.copy() if not isinstance(default, defaultdict) else defaultdict(default.default_factory)
            else:
                st.session_state[fk] = default

    def get(self, key: str, default: Any = None) -> Any:
        """
        Récupère la valeur d'une clé, retourne 'default' si absente.
        """
        fk = self._full_key(key)
        return st.session_state.get(fk, default)

    def set(self, key: str, value: Any):
        """
        Définit la valeur d'une clé.
        """
        st.session_state[self._full_key(key)] = value

    def toggle(self, key: str):
        """
        Inverse un booléen stocké dans une clé.
        """
        fk = self._full_key(key)
        st.session_state[fk] = not st.session_state.get(fk, False)

    def exists(self, key: str) -> bool:
        """
        Vérifie si une clé existe.
        """
        return self._full_key(key) in st.session_state

    def clear(self, key: str):
        """
        Supprime une clé du session_state.
        """
        st.session_state.pop(self._full_key(key), None)

    def init_bulk(self, defaults: dict):
        """
        Initialise plusieurs clés à la fois.
        """
        for k, v in defaults.items():
            self.init(k, v)

    def update(self, key: str, func: Callable[[Any], Any]):
        """
        Applique une fonction de transformation à la valeur d'une clé.
        """
        fk = self._full_key(key)
        self.set(key, func(st.session_state.get(fk)))

