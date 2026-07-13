import json
import tempfile
import unittest
from pathlib import Path

from human_ai.config import Config
from human_ai.public_apis import PublicApiCatalogStore, parse_public_apis_readme


class PublicApiCatalogTests(unittest.TestCase):
    def test_parse_public_apis_readme_table(self):
        readme = """
### Weather
API | Description | Auth | HTTPS | CORS |
|:---|:---|:---|:---|:---|
| [Open-Meteo](https://open-meteo.com/) | Weather forecast API | No | Yes | Yes |
| [Weatherstack](https://weatherstack.com/) | Weather API | `apiKey` | Yes | Unknown |

### Music
API | Description | Auth | HTTPS | CORS |
|:---|:---|:---|:---|:---|
| [MusicBrainz](https://musicbrainz.org/doc/MusicBrainz_API) | Music metadata | No | Yes | Unknown |
"""
        rows = parse_public_apis_readme(readme)
        self.assertEqual(len(rows), 3)
        self.assertEqual(rows[0].name, "Open-Meteo")
        self.assertEqual(rows[0].category, "Weather")
        self.assertEqual(rows[1].auth, "apiKey")
        self.assertEqual(rows[2].description, "Music metadata")

    def test_search_filters_cached_catalog(self):
        with tempfile.TemporaryDirectory() as temp:
            config = Config(workspace=Path(temp))
            store = PublicApiCatalogStore(config)
            store.cache_dir.mkdir(parents=True)
            store.cache_path.write_text(
                json.dumps(
                    {
                        "source": store.repo_url,
                        "license": "MIT",
                        "cached_at": "2026-07-08T00:00:00Z",
                        "categories": ["Music", "Weather"],
                        "entries": [
                            {
                                "name": "Open-Meteo",
                                "url": "https://open-meteo.com/",
                                "description": "Weather forecast API",
                                "auth": "No",
                                "https": "Yes",
                                "cors": "Yes",
                                "category": "Weather",
                            },
                            {
                                "name": "Weatherstack",
                                "url": "https://weatherstack.com/",
                                "description": "Weather API",
                                "auth": "apiKey",
                                "https": "Yes",
                                "cors": "Unknown",
                                "category": "Weather",
                            },
                        ],
                    }
                ),
                encoding="utf-8",
            )
            result = store.search(query="weather", no_auth_only=True, https_only=True)
        self.assertEqual(result["count"], 1)
        self.assertEqual(result["entries"][0]["name"], "Open-Meteo")


if __name__ == "__main__":
    unittest.main()
