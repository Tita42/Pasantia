from pathlib import Path
import json, numpy as np
from sentence_transformers import SentenceTransformer

def main():
    # ... parse args: --dict, --model, --out
    out_dir = Path(args.out).expanduser().resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    # cargar términos (id_word_map.json)
    id2terms = json.load(open(f"diccionarios/word_id_map.json"))
    terms = sorted({w for words in id2terms.values() for w in words})

    # SBERT
    model = SentenceTransformer(args.model)
    emb = model.encode(terms, batch_size=64, show_progress_bar=True, normalize_embeddings=True)

    # GUARDAR **EN out_dir**
    np.save(out_dir / "sbert_embeddings.npy", emb)
    with open(out_dir / "sbert_terms.json", "w", encoding="utf-8") as f:
        json.dump(terms, f, ensure_ascii=False, indent=2)

    print(f"Index listo en: {out_dir} ({len(terms)} términos)")

