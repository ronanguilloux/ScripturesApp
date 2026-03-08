import os
import contextlib
from src.adapters.text_fabric_adapter import TextFabricAdapter
from src.adapters.local_nlp_adapter import LocalNLPAdapter
from src.references_db import ReferenceDatabase
from tf.app import use

class DependencyContainer:
    _bible_adapter = None
    _nlp_adapter = None
    _ref_db = None
    
    @classmethod
    def get_bible_adapter(cls) -> TextFabricAdapter:
        if cls._bible_adapter:
            return cls._bible_adapter
            
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(current_dir)
        data_dir = os.path.join(project_root, "data")
        
        def n1904_p():
             with open(os.devnull, 'w') as f, contextlib.redirect_stdout(f):
                 try: return use("CenterBLC/N1904", version="1.0.0", silent=True)
                 except: return None
        
        def lxx_p():
             with open(os.devnull, 'w') as f, contextlib.redirect_stdout(f):
                 try: return use("CenterBLC/LXX", version="1935", check=False, silent=True)
                 except: return None

        adapter = TextFabricAdapter(
            data_dir=data_dir,
            n1904_provider=n1904_p,
            lxx_provider=lxx_p,
        )
        cls._bible_adapter = adapter
        return adapter

    @classmethod
    def get_nlp_adapter(cls) -> LocalNLPAdapter:
        if cls._nlp_adapter:
            return cls._nlp_adapter
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(current_dir)
        cls._nlp_adapter = LocalNLPAdapter(project_root)
        return cls._nlp_adapter

    @classmethod
    def get_ref_db(cls) -> ReferenceDatabase:
        if cls._ref_db:
             return cls._ref_db
        adapter = cls.get_bible_adapter()
        cls._ref_db = ReferenceDatabase(adapter.data_dir, adapter.normalizer)
        return cls._ref_db
