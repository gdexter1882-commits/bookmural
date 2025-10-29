# eligible_texts.py
import csv
import unicodedata
import re

CSV_PATH = "mural_master_regenerated.csv"

def slugify(text):
    if not isinstance(text, str):
        return ""
    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s-]+", "_", text)  # Match CSV underscore style
    return text.lower().strip("_")

def try_layout(wall_w, wall_h, page_w, page_h, pages, margin=0):
    for margin_test in range(5, 16):
        usable_w = wall_w - 2 * margin_test
        usable_h = wall_h - 2 * margin_test

        for scale_pct in range(95, 106):
            scaled_pw = page_w * scale_pct / 100
            scaled_ph = page_h * scale_pct / 100

            for row_gap in range(1, 6):
                for cols in range(1, pages + 1):
                    rows = (pages + cols - 1) // cols

                    mural_w = cols * scaled_pw
                    mural_h = rows * scaled_ph + (rows - 1) * row_gap

                    if mural_w <= usable_w and mural_h <= usable_h:
                        margin_x = (wall_w - mural_w) / 2
                        margin_y = (wall_h - mural_h) / 2

                        if not (5 <= margin_x <= 15 and 5 <= margin_y <= 15):
                            continue

                        return {
                            "eligible": True,
                            "grid": f"{rows}x{cols}",
                            "scale_pct": scale_pct,
                            "row_gap": row_gap,
                            "margin_x": round(margin_x, 2),
                            "margin_y": round(margin_y, 2),
                            "page_w": round(scaled_pw, 2),
                            "page_h": round(scaled_ph, 2),
                            "text_centered": True
                        }

    return {"eligible": False}

def get_eligible_texts(wall_width, wall_height, csv_path=CSV_PATH, cdn_map=None):
    eligible = []

    # =================================================================
    # SHOPIFY COVER IMAGE MAPPING (HIGH-RES, 600x900px, ~150KB)
    # =================================================================
    shopify_covers = {
        # Crane
        "crane_stephen_the_red_badge_of_courage_1898_facsimile_235": 
            "https://cdn.shopify.com/s/files/1/0834/3761/9517/files/crane-stephen-the-red-badge-of-courage-1898-facsimile-235.jpg",
        
        # Dickens
        "dickens_charles_four_stories_captain_boldheart_mrs_orange_and_mrs_lemon_little_bebelle_the_story_of_the_goblins_who_stole_a_sexton_77": 
            "https://cdn.shopify.com/s/files/1/0834/3761/9517/files/dickens-charles-four-stories-captain-boldheart-77.jpg",
        "dickens_charles_three_stories_gone_astray_william_tinkling_the_magic_fishbone_facsimile_49": 
            "https://cdn.shopify.com/s/files/1/0834/3761/9517/files/dickens-charles-three-stories-gone-astray-49.jpg",
        "dickens_charles_two_stories_mugby_junction_a_childs_dream_of_a_star_facsimile_42": 
            "https://cdn.shopify.com/s/files/1/0834/3761/9517/files/dickens-charles-two-stories-mugby-junction-42.jpg",

        # Forster
        "forster_em_2_stories_the_story_of_a_panic_the_other_side_of_the_hedge_1912_facsimile_57": 
            "https://cdn.shopify.com/s/files/1/0834/3761/9517/files/forster-em-2-stories-the-story-of-a-panic-57.jpg",
        "forster_em_3_stories_other_kingdom_the_curates_friend_the_road_from_colonus_1912_facsimile_82": 
            "https://cdn.shopify.com/s/files/1/0834/3761/9517/files/forster-em-3-stories-other-kingdom-82.jpg",
        "forster_em_3_stories_the_story_of_a_panic_the_other_side_of_the_hedge_the_celestial_omnibus_1912_facsimile_87": 
            "https://cdn.shopify.com/s/files/1/0834/3761/9517/files/forster-em-3-stories-the-celestial-omnibus-87.jpg",
        "forster_em_the_celestial_omnibus_complete_6_stories_1912_facsimile_169": 
            "https://cdn.shopify.com/s/files/1/0834/3761/9517/files/forster-em-the-celestial-omnibus-complete-169.jpg",

        # Hardy
        "hardy_thomas_2_wessex_tales_an_imaginative_woman_and_the_three_strangers_1896_facsimile_60": 
            "https://cdn.shopify.com/s/files/1/0834/3761/9517/files/hardy-thomas-2-wessex-tales-an-imaginative-woman-60.jpg",
        "hardy_thomas_2_wessex_tales_the_withered_arm_and_the_distracted_preacher_1896_facsimile_116": 
            "https://cdn.shopify.com/s/files/1/0834/3761/9517/files/hardy-thomas-2-wessex-tales-the-withered-arm-116.jpg",
        "hardy_thomas_the_distracted_preacher_1896_facsimile_75": 
            "https://cdn.shopify.com/s/files/1/0834/3761/9517/files/hardy-thomas-the-distracted-preacher-75.jpg",
        "hardy_thomas_the_withered_arm_1896_facsimile_42": 
            "https://cdn.shopify.com/s/files/1/0834/3761/9517/files/hardy-thomas-the-withered-arm-42.jpg",
        "hardy_thomas_wessex_tales": 
            "https://cdn.shopify.com/s/files/1/0834/3761/9517/files/hardy-thomas-wessex-tales-297.jpg",

        # Johnson
        "johnson_samuel_rasselas_1960_facsimile_125": 
            "https://cdn.shopify.com/s/files/1/0834/3761/9517/files/johnson-samuel-rasselas-125.jpg",

        # Joyce
        "joyce_james_3_stories_from_dubliners_a_mother_grace_the_dead_1914_facsimile_120": 
            "https://cdn.shopify.com/s/files/1/0834/3761/9517/files/joyce-james-3-stories-a-mother-grace-the-dead-120.jpg",
        "joyce_james_5_stories_from_dubliners_a_little_cloud_counterparts_clay_a_painful_case_ivy_day_in_the_committee_room_1914_facsimile_89": 
            "https://cdn.shopify.com/s/files/1/0834/3761/9517/files/joyce-james-5-stories-a-little-cloud-89.jpg",
        "joyce_james_7_stories_from_dubliners_the_sisters_an_encounter_araby_eveline_after_the_race_two_gallants_the_boarding_house_1914_facsimile_82": 
            "https://cdn.shopify.com/s/files/1/0834/3761/9517/files/joyce-james-7-stories-the-sisters-82.jpg",
        "joyce_james_dubliners_complete_1914_facsimile_278": 
            "https://cdn.shopify.com/s/files/1/0834/3761/9517/files/joyce-james-dubliners-complete-278.jpg",

        # Mansfield
        "mansfield_katherine_bliss_and_other_stories_1921_facsimile_287": 
            "https://cdn.shopify.com/s/files/1/0834/3761/9517/files/mansfield-katherine-bliss-and-other-stories-287.jpg",
        "mansfield_katherine_prelude_1921_facsimile_77": 
            "https://cdn.shopify.com/s/files/1/0834/3761/9517/files/mansfield-katherine-prelude-77.jpg",
        "mansfield_katherine_seven_stories_from_bliss_1921_facsimile_88": 
            "https://cdn.shopify.com/s/files/1/0834/3761/9517/files/mansfield-katherine-seven-stories-from-bliss-88.jpg",
        "mansfield_katherine_six_stories_from_bliss_including_title_story_1921_facsimile_124": 
            "https://cdn.shopify.com/s/files/1/0834/3761/9517/files/mansfield-katherine-six-stories-from-bliss-124.jpg",

        # Wells
        "wells_hg_2_stories_from_the_collection_t": 
            "https://cdn.shopify.com/s/files/1/0834/3761/9517/files/wells-hg-2-stories-from-the-collection-42.jpg",
        "wells_hg_3_stories_from_the_collection_t": 
            "https://cdn.shopify.com/s/files/1/0834/3761/9517/files/wells-hg-3-stories-from-the-collection-65.jpg",
        "wells_hg_4_stories_from_the_collection_t": 
            "https://cdn.shopify.com/s/files/1/0834/3761/9517/files/wells-hg-4-stories-from-the-collection-95.jpg",
        "wells_hg_9_stories_from_the_collection_t": 
            "https://cdn.shopify.com/s/files/1/0834/3761/9517/files/wells-hg-9-stories-from-the-collection-186.jpg",

        # Wilde
        "wilde_oscar_lord_arthur_saviles_crime_an": 
            "https://cdn.shopify.com/s/files/1/0834/3761/9517/files/wilde-oscar-lord-arthur-saviles-crime-163.jpg",
        "wilde_oscar_five_stories_the_happy_princ": 
            "https://cdn.shopify.com/s/files/1/0834/3761/9517/files/wilde-oscar-five-stories-the-happy-prince-118.jpg",
        "wilde_oscar_four_stories_the_happy_princ": 
            "https://cdn.shopify.com/s/files/1/0834/3761/9517/files/wilde-oscar-four-stories-the-happy-prince-81.jpg",
        "wilde_oscar_the_happy_prince_1908_facsim": 
            "https://cdn.shopify.com/s/files/1/0834/3761/9517/files/wilde-oscar-the-happy-prince-23.jpg",
        "wilde_oscar_the_nightingale_and_the_rose": 
            "https://cdn.shopify.com/s/files/1/0834/3761/9517/files/wilde-oscar-the-nightingale-and-the-rose-15.jpg",
        "wilde_oscar_the_selfish_giant_1908_facsi": 
            "https://cdn.shopify.com/s/files/1/0834/3761/9517/files/wilde-oscar-the-selfish-giant-11.jpg",
        "wilde_oscar_the_star_child_1908_facsimil": 
            "https://cdn.shopify.com/s/files/1/0834/3761/9517/files/wilde-oscar-the-star-child-37.jpg",
        "wilde_oscar_the_young_king_1908_facsimil": 
            "https://cdn.shopify.com/s/files/1/0834/3761/9517/files/wilde-oscar-the-young-king-32.jpg",
        "wilde_oscar_three_stories_the_happy_prin": 
            "https://cdn.shopify.com/s/files/1/0834/3761/9517/files/wilde-oscar-three-stories-the-happy-prince-49.jpg",
        "wilde_oscar_two_stories_the_happy_prince": 
            "https://cdn.shopify.com/s/files/1/0834/3761/9517/files/wilde-oscar-two-stories-the-happy-prince-34.jpg",

        # Wodehouse
        "wodehouse_pg_11_pg_wodehouse_stories_fea": 
            "https://cdn.shopify.com/s/files/1/0834/3761/9517/files/wodehouse-pg-11-stories-blandings-281.jpg",
        "wodehouse_pg_2_selected_mr_mulliner_stor": 
            "https://cdn.shopify.com/s/files/1/0834/3761/9517/files/wodehouse-pg-2-mr-mulliner-45.jpg",
        "wodehouse_pg_2_wodehouse_blandings_stori": 
            "https://cdn.shopify.com/s/files/1/0834/3761/9517/files/wodehouse-pg-2-blandings-58.jpg",
        "wodehouse_pg_3_pg_wodehouse_blandings_st": 
            "https://cdn.shopify.com/s/files/1/0834/3761/9517/files/wodehouse-pg-3-blandings-85.jpg",
        "wodehouse_pg_4_pg_wodehouse_blandings_st": 
            "https://cdn.shopify.com/s/files/1/0834/3761/9517/files/wodehouse-pg-4-blandings-110.jpg",
        "wodehouse_pg_4_selected_mr_mulliner_stor": 
            "https://cdn.shopify.com/s/files/1/0834/3761/9517/files/wodehouse-pg-4-mr-mulliner-91.jpg",
        "wodehouse_pg_5_blandings_stories_the_cus": 
            "https://cdn.shopify.com/s/files/1/0834/3761/9517/files/wodehouse-pg-5-blandings-136.jpg",
        "wodehouse_pg_7_pg_wodehouse_blandings_st": 
            "https://cdn.shopify.com/s/files/1/0834/3761/9517/files/wodehouse-pg-7-blandings-191.jpg",

        # Woolf
        "woolf_virginia_a_room_of_ones_own_1935_f": 
            "https://cdn.shopify.com/s/files/1/0834/3761/9517/files/woolf-virginia-a-room-of-ones-own-172.jpg",
        "woolf_virginia_mrs_dalloway_1925_facsimi": 
            "https://cdn.shopify.com/s/files/1/0834/3761/9517/files/woolf-virginia-mrs-dalloway-296.jpg"
    }

    try:
        with open(csv_path, newline="", encoding="utf-8") as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                try:
                    handle = str(row.get("Handle", "")).strip()
                    title = str(row.get("Title", "")).strip()
                    pages = int(row.get("Pages", 0))
                    width_cm = float(row.get("Page Width (cm)", 0))
                    height_cm = float(row.get("Page Height (cm)", 0))

                    if height_cm == 0:
                        continue

                    aspect_ratio = round(width_cm / height_cm, 4)
                    layout = try_layout(wall_width, wall_height, width_cm, height_cm, pages)

                    if layout.get("eligible"):
                        # Forensic thumbnail lookup (fallback)
                        thumbnail_url = None
                        for key, url in cdn_map.items():
                            key_folder = key.rsplit("/", 1)[0]
                            slug = slugify(key_folder)
                            if slug == handle and key.lower().endswith("page_001.jpg"):
                                thumbnail_url = url
                                print(f"Matched thumbnail: {key}", flush=True)
                                break

                        if not thumbnail_url:
                            print(f"Thumbnail not found in cdn_map for handle: {handle}", flush=True)

                        # Use Shopify cover if available, else fallback to R2
                        cover_url = shopify_covers.get(handle, "")

                        eligible.append({
                            "title": title,
                            "handle": handle,
                            "slug": slugify(handle),
                            "grid": layout.get("grid"),
                            "scale": layout.get("scale_pct"),
                            "thumbnail": thumbnail_url or "",  # R2 fallback
                            "cover_url": cover_url,           # Shopify high-res cover
                            "pages": pages,
                            "aspect_ratio": aspect_ratio,
                            "page_w": width_cm,
                            "page_h": height_cm,
                            "folder": title.rsplit(" (", 1)[0] + f" ({pages})"
                        })
                except Exception as e:
                    print(f"Skipping row due to error: {e}", flush=True)
        print(f"Reloaded {csv_path} with {len(eligible)} eligible entries", flush=True)
    except Exception as e:
        print(f"Failed to load {csv_path}: {e}", flush=True)

    return eligible