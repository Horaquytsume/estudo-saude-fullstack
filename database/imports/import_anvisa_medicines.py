#!/usr/bin/env python3
"""Importa registros ativos da base pública de medicamentos da Anvisa para MySQL.

Uso:
  python import_anvisa_medicines.py --dry-run
  python import_anvisa_medicines.py --file DADOS_ABERTOS_MEDICAMENTOS.csv
  python import_anvisa_medicines.py

O arquivo oficial está em CP-1252 e separado por ponto e vírgula. Os dados
importados são registros regulatórios; não representam aconselhamento clínico.
"""
import argparse
import csv
import hashlib
import os
import sys
import urllib.request
from datetime import date
from pathlib import Path

SOURCE_URL = "https://dados.anvisa.gov.br/dados/DADOS_ABERTOS_MEDICAMENTOS.csv"
BATCH_SIZE = 500


def normalized(row):
    def val(key):
        return (row.get(key) or "").strip()
    return {
        "product_name": val("NOME_PRODUTO"),
        "active_ingredient": val("PRINCIPIO_ATIVO"),
        "therapeutic_class": val("CLASSE_TERAPEUTICA"),
        "category": val("CATEGORIA_REGULATORIA"),
        "registration_number": val("NUMERO_REGISTRO_PRODUTO"),
        "company": val("EMPRESA_DETENTORA_REGISTRO"),
        "status": val("SITUACAO_REGISTRO"),
        "registration_expiry": val("DATA_VENCIMENTO_REGISTRO"),
    }


def record_hash(item):
    raw = "|".join(item.values()).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def stable_key(item):
    # Prefer a registro number to let reimports update status instead of duplicating rows.
    identity = "|".join((item["registration_number"], item["product_name"].casefold(), item["company"].casefold(), item["active_ingredient"].casefold()))
    return hashlib.sha256(identity.encode("utf-8")).hexdigest()


def parse_file(path):
    with open(path, "r", encoding="cp1252", newline="") as f:
        reader = csv.DictReader(f, delimiter=";")
        required = {"NOME_PRODUTO", "SITUACAO_REGISTRO"}
        if not reader.fieldnames or not required.issubset(reader.fieldnames):
            raise ValueError("CSV sem as colunas esperadas da base de medicamentos Anvisa.")
        for row in reader:
            item = normalized(row)
            if item["product_name"]:
                yield item


def download():
    dest = Path("data/DADOS_ABERTOS_MEDICAMENTOS.csv")
    dest.parent.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(SOURCE_URL, headers={"User-Agent": "EstudoSaude/1.0 (educational importer)"})
    with urllib.request.urlopen(request, timeout=120) as response, dest.open("wb") as output:
        while True:
            chunk = response.read(1024 * 1024)
            if not chunk:
                break
            output.write(chunk)
    return dest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--file", help="CSV oficial já baixado; omita para baixar da Anvisa")
    parser.add_argument("--dry-run", action="store_true", help="Conta registros ativos sem conectar ao MySQL")
    args = parser.parse_args()
    source = Path(args.file) if args.file else download()
    rows = parse_file(source)
    if args.dry_run:
        count = active_rows = 0
        names = set()
        keys = set()
        active_keys = set()
        for item in rows:
            count += 1
            names.add(item["product_name"].casefold())
            key = stable_key(item)
            keys.add(key)
            if item["status"].casefold() == "ativo":
                active_rows += 1
                active_keys.add(key)
        print(f"Prévia: {count} linhas; {len(keys)} chaves distintas ({len(active_keys)} ativas distintas); {active_rows} linhas marcadas ATIVO; {len(names)} nomes distintos.")
        print("A fonte registra produtos/apresentações regulatórias, não princípios ativos únicos nem recomendações clínicas.")
        return 0

    try:
        import mysql.connector
        from dotenv import load_dotenv
        # Load the local backend configuration if present; container env vars take precedence.
        load_dotenv(Path(__file__).resolve().parents[2] / "backend" / ".env", override=False)
    except ImportError:
        print("Dependência ausente. Instale python-engine/requirements.txt", file=sys.stderr)
        return 2

    db = mysql.connector.connect(
        host=os.getenv("DB_HOST", "127.0.0.1"),
        port=int(os.getenv("DB_PORT", "3306")),
        user=os.getenv("DB_USER", "estudo_saude_app"),
        password=os.getenv("DB_PASSWORD", ""),
        database=os.getenv("DB_NAME", "estudo_saude"),
        charset="utf8mb4",
        autocommit=False,
    )
    sql = """INSERT INTO anvisa_medicines
      (source_key, source_hash, product_name, active_ingredient, therapeutic_class, category,
       registration_number, company, status, registration_expiry, source_name, imported_at)
      VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'Anvisa - Dados Abertos',CURRENT_TIMESTAMP)
      ON DUPLICATE KEY UPDATE source_hash=VALUES(source_hash), product_name=VALUES(product_name),
       active_ingredient=VALUES(active_ingredient), therapeutic_class=VALUES(therapeutic_class),
       category=VALUES(category), registration_number=VALUES(registration_number),
       company=VALUES(company), status=VALUES(status), registration_expiry=VALUES(registration_expiry),
       imported_at=CURRENT_TIMESTAMP"""
    batch = []
    total = 0
    try:
        cursor = db.cursor()
        for item in rows:
            batch.append((stable_key(item), record_hash(item), item["product_name"], item["active_ingredient"],
                          item["therapeutic_class"], item["category"], item["registration_number"],
                          item["company"], item["status"], item["registration_expiry"]))
            if len(batch) >= BATCH_SIZE:
                cursor.executemany(sql, batch)
                db.commit()
                total += len(batch)
                print(f"Importados/processados: {total}", flush=True)
                batch.clear()
        if batch:
            cursor.executemany(sql, batch)
            db.commit()
            total += len(batch)
        print(f"Concluído: {total} registros regulatórios importados/atualizados.")
        print("Registros oficiais não incluem necessariamente bula, indicação clínica ou dose.")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"Falha na importação: {exc}", file=sys.stderr)
        raise SystemExit(1)
