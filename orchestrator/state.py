import sqlite3
from typing import Optional
import os
import json

class StateDB:
    def __init__(self, db_path="state.db"):
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self._create_table()

    def _create_table(self):
        # Add new columns caption and tags (tags stored as JSON string)
        self.conn.execute("""
        CREATE TABLE IF NOT EXISTS published_products (
            product_title TEXT PRIMARY KEY,
            fake_product_id TEXT,
            mockup_url TEXT,
            caption TEXT,
            tags TEXT,
            published_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        self.conn.commit()

    def is_published(self, title: str) -> bool:
        cur = self.conn.execute("SELECT 1 FROM published_products WHERE product_title = ?", (title,))
        return cur.fetchone() is not None

    def save_record(self, title: str, fake_product_id: str, mockup_url: str, caption: Optional[str] = "", tags: Optional[list] = None):
        tags_json = json.dumps(tags or [])
        self.conn.execute("""
            INSERT OR REPLACE INTO published_products (product_title, fake_product_id, mockup_url, caption, tags)
            VALUES (?, ?, ?, ?, ?)
        """, (title, fake_product_id, mockup_url, caption, tags_json))
        self.conn.commit()

    def get_all_records(self):
        cur = self.conn.execute("SELECT product_title, fake_product_id, mockup_url, caption, tags, published_at FROM published_products")
        rows = cur.fetchall()
        products = []
        for row in rows:
            mockup_url = row["mockup_url"]
            if os.path.isabs(mockup_url):
                filename = os.path.basename(mockup_url)
                mockup_url = f"http://localhost:3000/output/{filename}"
            products.append({
                "product_title": row["product_title"],
                "fake_product_id": row["fake_product_id"],
                "mockup_url": mockup_url,
                "caption": row["caption"],
                "tags": json.loads(row["tags"] or "[]"),
                "published_at": row["published_at"],
            })
        return products
