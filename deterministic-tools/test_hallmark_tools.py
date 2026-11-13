#!/usr/bin/env python3
"""Tests for hallmark_tools — tiered gates, kept, words, deal,
rotation, brief. Run: python3 -m unittest test_hallmark_tools -v"""

import json
import tempfile
import unittest
from pathlib import Path

import hallmark_tools as ht

PAGE = """<!doctype html><html><head><style>
:root { --ink: #33424f; }
body { color: var(--ink); }
</style></head><body>
<header><h1>Book a table</h1><p>Real food, tonight.</p>
<a href="/book">Book now</a></header>
<section><h2>Menu</h2><p>Short menu, cooked fresh.</p>
<img src="dish.jpg" alt="dish">
<form><input name="email" type="email">
<input name="party" type="number" onfocus="track()"></form>
<div id="hours" data-testid="hours-box">Open late</div>
</section><footer>Find us downtown</footer>
</body></html>"""

PAGE_DROPPED = PAGE.replace('<a href="/book">Book now</a>', "")


class Tmp(unittest.TestCase):
    def setUp(self):
        self.d = Path(tempfile.mkdtemp())

    def write(self, name, text):
        p = self.d / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
        return str(p)


class TestSnapshotKept(Tmp):
    def test_snapshot_counts(self):
        f = self.write("page.html", PAGE)
        out = str(self.d / "before.json")
        code, pay = ht.snapshot(f, out)
        self.assertEqual(code, 0)
        self.assertEqual(pay["kinds"]["link"], 1)
        self.assertEqual(pay["kinds"]["field"], 2)
        self.assertEqual(pay["kinds"]["hook"], 1)

    def test_kept_pass_identical(self):
        f = self.write("page.html", PAGE)
        out = str(self.d / "before.json")
        ht.snapshot(f, out)
        code, pay = ht.kept(out, f)
        self.assertEqual(code, 0)
        self.assertEqual(pay["kept"]["link"], "1/1")
        self.assertEqual(pay["verdict"], "PASS")

    def test_kept_fail_dropped_link(self):
        f = self.write("page.html", PAGE)
        out = str(self.d / "before.json")
        ht.snapshot(f, out)
        f2 = self.write("page2.html", PAGE_DROPPED)
        code, pay = ht.kept(out, f2)
        self.assertEqual(code, 1)
        self.assertIn("link:/book", pay["missing_fail"])

    def test_kept_dropped_recorded(self):
        f = self.write("page.html", PAGE)
        out = str(self.d / "before.json")
        ht.snapshot(f, out)
        f2 = self.write("page2.html", PAGE_DROPPED)
        code, pay = ht.kept(out, f2, dropped=["link:/book"])
        self.assertEqual(code, 0)
        self.assertIn("link:/book", pay["dropped_recorded"])

    def test_kept_heading_loss_is_warn_only(self):
        f = self.write("page.html", PAGE)
        out = str(self.d / "before.json")
        ht.snapshot(f, out)
        f2 = self.write("page2.html", PAGE.replace("<h2>Menu</h2>",
                                                   "<h2>Food</h2>"))
        code, pay = ht.kept(out, f2)
        self.assertEqual(code, 0)
        self.assertTrue(pay["missing_warn"])


class TestWords(Tmp):
    def test_card_budget_fail(self):
        long_text = "word " * 45
        f = self.write("card.txt", long_text)
        code, pay = ht.words(f, surface="card")
        self.assertEqual(code, 1)
        self.assertGreater(pay["total_words"], pay["total_budget"])

    def test_card_budget_pass(self):
        f = self.write("card.txt", "Fresh bread today. Warm and ready.")
        code, pay = ht.words(f, surface="card")
        self.assertEqual(code, 0)
        self.assertEqual(pay["verdict"], "PASS")

    def test_web_budget_pass_small_page(self):
        f = self.write("page.html", PAGE)
        code, pay = ht.words(f, surface="web")
        self.assertEqual(code, 0)

    def test_bad_surface(self):
        f = self.write("card.txt", "hi")
        code, _ = ht.words(f, surface="billboard")
        self.assertEqual(code, 2)


class TestGatecheck(Tmp):
    def test_clean_page_passes(self):
        f = self.write("page.html", PAGE)
        code, pay = ht.gatecheck(f, surface="web")
        self.assertEqual(code, 0, pay)
        self.assertEqual(pay["floor_fail"], 0)

    def test_lorem_is_floor_fail(self):
        f = self.write("page.html", PAGE.replace("Real food",
                                                 "Lorem ipsum"))
        code, pay = ht.gatecheck(f, surface="web")
        self.assertEqual(code, 1)
        self.assertEqual(pay["floor_fail"], 1)

    def test_gradient_floor_on_web_reflex_on_social(self):
        page = PAGE.replace("</style>",
                            ".x{background:linear-gradient(90deg, "
                            "purple, blue);}</style>")
        f = self.write("page.html", page)
        code, pay = ht.gatecheck(f, surface="web")
        self.assertEqual(code, 1)
        g = [r for r in pay["findings"] if r["gate"] == "gradient-pb"]
        self.assertEqual(g[0]["tier"], "floor")
        code2, pay2 = ht.gatecheck(f, surface="social")
        g2 = [r for r in pay2["findings"] if r["gate"] == "gradient-pb"]
        self.assertEqual(g2[0]["tier"], "reflex")
        self.assertEqual(code2, 1)  # unwaived reflex still blocks

    def test_reflex_waiver_accepted(self):
        page = PAGE.replace("</body>",
                            "<p>Fresh bread today \U0001F600</p>"
                            "</body>")
        f = self.write("page.html", page + "\n<!-- waive emoji-icon | "
                       "the photo itself carries the smile | the client "
                       "asked for one emoji on this card -->\n")
        code, pay = ht.gatecheck(f, surface="social")
        self.assertEqual(code, 0, pay)
        self.assertEqual(pay["waived"], 1)

    def test_reflex_waiver_too_short_rejected(self):
        page = PAGE + "\n<!-- waive emoji-icon | x | looks fine -->\n"
        page = page.replace("</body>", "<p>Hi \U0001F600</p></body>")
        f = self.write("page.html", page)
        code, pay = ht.gatecheck(f, surface="social")
        self.assertEqual(code, 1)
        self.assertEqual(pay["reflex_open"], 1)

    def test_floor_waiver_rejected(self):
        page = PAGE.replace("Real food", "Lorem ipsum")
        page += ("\n<!-- waive lorem | placeholder is intentional here "
                 "| the client wants latin on this draft page -->\n")
        f = self.write("page.html", page)
        code, pay = ht.gatecheck(f, surface="web")
        self.assertEqual(code, 1)
        g = [r for r in pay["findings"] if r["gate"] == "lorem"]
        self.assertIn("rejected", g[0]["status"])

    def test_caps_label_scoped_by_surface(self):
        page = PAGE.replace("<h2>Menu</h2>",
                            "<h2>FRESH HOT BREAD DAILY</h2>")
        f = self.write("page.html", page)
        _, pay_web = ht.gatecheck(f, surface="web")
        g = [r for r in pay_web["findings"] if r["gate"] == "caps-label"]
        self.assertTrue(g and g[0]["tier"] == "floor")
        _, pay_soc = ht.gatecheck(f, surface="social")
        g2 = [r for r in pay_soc["findings"] if r["gate"] == "caps-label"]
        self.assertTrue(g2 and g2[0]["tier"] == "reflex")

    def test_finish_never_blocks(self):
        page = PAGE.replace("<footer>Find us downtown</footer>", "")
        f = self.write("page.html", page)
        code, pay = ht.gatecheck(f, surface="web")
        self.assertEqual(code, 0)
        self.assertTrue(any(x["check"] == "finish:footer"
                            for x in pay["finish"]))

    def test_hero_stage_words(self):
        hero = " ".join(["word"] * 35)
        page = PAGE.replace("Real food, tonight.", hero)
        f = self.write("page.html", page)
        code, pay = ht.gatecheck(f, surface="web", stage="hero")
        self.assertEqual(code, 1)
        self.assertTrue(any(r["gate"] == "words"
                            for r in pay["findings"]))


class TestDealRotation(Tmp):
    def themes(self):
        d = self.d / "themes"
        d.mkdir()
        for name in ("coral", "cobalt", "paper", "kiln", "dusk"):
            (d / f"{name}.md").write_text(f"# {name}\nmaterial",
                                          encoding="utf-8")
        return str(d)

    def test_deal_three(self):
        code, pay = ht.deal(self.themes(), prompt="bakery")
        self.assertEqual(code, 0)
        self.assertEqual(len(pay["dealt"]), 3)

    def test_deal_clears_recent_log(self):
        log = str(self.d / "log.json")
        ht.rotation("add", log, entry={"theme": "coral",
                                       "shape": "stage"})
        code, pay = ht.deal(self.themes(), log_path=log, prompt="bakery")
        self.assertEqual(code, 0)
        self.assertNotIn("coral", [t["slug"] for t in pay["dealt"]])
        self.assertIn("coral", pay["cleared_recent"])

    def test_rotation_mirror_fail(self):
        log = str(self.d / "log.json")
        entry = {"theme": "coral", "shape": "stage", "hero": "left",
                 "nav": "edge", "footer": "mast", "signature": "oven"}
        ht.rotation("add", log, entry=entry)
        code, pay = ht.rotation("check", log, entry=dict(entry))
        self.assertEqual(code, 1)
        self.assertEqual(pay["mirror_test"], "FAIL")

    def test_rotation_mirror_pass_when_different(self):
        log = str(self.d / "log.json")
        ht.rotation("add", log, entry={"theme": "coral",
                                       "shape": "stage", "hero": "left",
                                       "nav": "edge", "footer": "mast",
                                       "signature": "oven"})
        code, pay = ht.rotation("check", log,
                                entry={"theme": "kiln", "shape": "index",
                                       "hero": "top", "nav": "side",
                                       "footer": "flat",
                                       "signature": "loaf"})
        self.assertEqual(code, 0)

    def test_house_style_gate(self):
        log = str(self.d / "log.json")
        for i in range(3):
            ht.rotation("add", log, entry={"theme": f"t{i}",
                                           "waived": "caps-label"})
        code, pay = ht.rotation("check", log, entry={"theme": "new"})
        self.assertIn("caps-label", pay["house_style_gates"])


class TestBrief(Tmp):
    BASE = dict(surface="social", job="save this post",
                shape="stage", theme="coral", signature="the oven door",
                real="fresh sourdough, made today", pictures="client photo",
                absent="no prices, no quotes")

    def test_brief_writes_stamp(self):
        out = str(self.d / "stamp.txt")
        code, pay = ht.brief(out, critique="P5 H4 E5 S3 R5 V4",
                             **self.BASE)
        self.assertEqual(code, 0)
        text = Path(out).read_text(encoding="utf-8")
        self.assertIn("absent: no prices", text)
        self.assertIn("fresh-context review", text)
        self.assertEqual(pay["weakest"], "S")

    def test_brief_absent_must_be_declared(self):
        out = str(self.d / "stamp.txt")
        bad = dict(self.BASE, absent="")
        code, pay = ht.brief(out, **bad)
        self.assertEqual(code, 2)
        self.assertIn("absent", pay["error"])

    def test_brief_low_critique_triggers_revision(self):
        out = str(self.d / "stamp.txt")
        code, pay = ht.brief(out, critique="P2 H4 E5 S3 R5 V4",
                             **self.BASE)
        self.assertEqual(code, 1)
        self.assertTrue(pay["revision_required"])

    def test_brief_theme_over_8kb_fails(self):
        big = self.write("big-theme.md", "x" * 9000)
        out = str(self.d / "stamp.txt")
        code, pay = ht.brief(out, theme_file=big, **self.BASE)
        self.assertEqual(code, 1)
        self.assertTrue(pay["theme_over_8kb"])


if __name__ == "__main__":
    unittest.main()
