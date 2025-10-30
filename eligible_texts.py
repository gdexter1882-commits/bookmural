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
    text = re.sub(r"[\s-]+", "_", text)
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
    # SHOPIFY HIGH-RES COVER IMAGES — ALL 64 FILES WITH 'x' PREFIX
    # CORRECTED: Full title + pages in filename, with ?v= timestamp
    # =================================================================
    shopify_covers = {
        # Crane
        "crane_stephen_the_red_badge_of_courage_1898_facsimile_235": 
            "https://cdn.shopify.com/s/files/1/0960/9930/3717/files/xCrane_Stephen_The_Red_Badge_of_Courage_1898_facsimile_235.jpg?v=1761788882",

        # Dickens
        "dickens_charles_four_stories_captain_boldheart_mrs_orange_and_mrs_lemon_little_bebelle_the_story_of_the_goblins_who_stole_a_sexton_77": 
            "https://cdn.shopify.com/s/files/1/0960/9930/3717/files/xDickens_Charles_Four_Stories_Captain_Boldheart_Mrs_Orange_and_Mrs_Lemon_Little_Bebelle_The_Story_of_the_Goblins_who_Stole_a_Sexton_77.jpg?v=1761788882",
        "dickens_charles_three_stories_gone_astray_william_tinkling_the_magic_fishbone_facsimile_49": 
            "https://cdn.shopify.com/s/files/1/0960/9930/3717/files/xDickens_Charles_Three_Stories_Gone_Astray_William_Tinkling_The_Magic_Fishbone_facsimile_49.jpg?v=1761788882",
        "dickens_charles_two_stories_mugby_junction_a_childs_dream_of_a_star_facsimile_42": 
            "https://cdn.shopify.com/s/files/1/0960/9930/3717/files/xDickens_Charles_Two_Stories_Mugby_Junction_A_Child_s_Dream_of_a_Star_facsimile_42.jpg?v=1761788882",

        # Forster
        "forster_em_2_stories_the_story_of_a_panic_the_other_side_of_the_hedge_1912_facsimile_57": 
            "https://cdn.shopify.com/s/files/1/0960/9930/3717/files/xForster_EM_2_Stories_The_Story_of_a_Panic_The_Other_Side_of_the_Hedge_1912_facsimile_57.jpg?v=1761788882",
        "forster_em_3_stories_other_kingdom_the_curates_friend_the_road_from_colonus_1912_facsimile_82": 
            "https://cdn.shopify.com/s/files/1/0960/9930/3717/files/xForster_EM_3_Stories_Other_Kingdom_The_Curates_Friend_The_Road_from_Colonus_1912_facsimile_82.jpg?v=1761788882",
        "forster_em_3_stories_the_story_of_a_panic_the_other_side_of_the_hedge_the_celestial_omnibus_1912_facsimile_87": 
            "https://cdn.shopify.com/s/files/1/0960/9930/3717/files/xForster_EM_3_Stories_The_Story_of_a_Panic_The_Other_Side_of_the_Hedge_The_Celestial_Omnibus_1912_facsimile_87.jpg?v=1761788882",
        "forster_em_the_celestial_omnibus_complete_6_stories_1912_facsimile_169": 
            "https://cdn.shopify.com/s/files/1/0960/9930/3717/files/xForster_EM_The_Celestial_Omnibus_Complete_6_Stories_1912_facsimile_169.jpg?v=1761788882",

        # Hardy
        "hardy_thomas_2_wessex_tales_an_imaginative_woman_and_the_three_strangers_1896_facsimile_60": 
            "https://cdn.shopify.com/s/files/1/0960/9930/3717/files/xHardy_Thomas_2_Wessex_Tales_An_Imaginative_Woman_and_the_Three_Strangers_1896_facsimile_60.jpg?v=1761788882",
        "hardy_thomas_2_wessex_tales_the_withered_arm_and_the_distracted_preacher_1896_facsimile_116": 
            "https://cdn.shopify.com/s/files/1/0960/9930/3717/files/xHardy_Thomas_2_Wessex_Tales_The_Withered_Arm_and_the_Distracted_Preacher_1896_facsimile_116.jpg?v=1761788882",
        "hardy_thomas_the_distracted_preacher_1896_facsimile_75": 
            "https://cdn.shopify.com/s/files/1/0960/9930/3717/files/xHardy_Thomas_The_Distracted_Preacher_1896_facsimile_75.jpg?v=1761788882",
        "hardy_thomas_the_withered_arm_1896_facsimile_42": 
            "https://cdn.shopify.com/s/files/1/0960/9930/3717/files/xHardy_Thomas_The_Withered_Arm_1896_facsimile_42.jpg?v=1761788882",
        "hardy_thomas_wessex_tales": 
            "https://cdn.shopify.com/s/files/1/0960/9930/3717/files/xHardy_Thomas_Wessex_Tales_297.jpg?v=1761788882",

        # Johnson
        "johnson_samuel_rasselas_1960_facsimile_125": 
            "https://cdn.shopify.com/s/files/1/0960/9930/3717/files/xJohnson_Samuel_Rasselas_1960_facsimile_125.jpg?v=1761788882",

        # Joyce
        "joyce_james_3_stories_from_dubliners_a_mother_grace_the_dead_1914_facsimile_120": 
            "https://cdn.shopify.com/s/files/1/0960/9930/3717/files/xJoyce_James_3_Stories_from_Dubliners_A_Mother_Grace_The_Dead_1914_facsimile_120.jpg?v=1761788882",
        "joyce_james_5_stories_from_dubliners_a_little_cloud_counterparts_clay_a_painful_case_ivy_day_in_the_committee_room_1914_facsimile_89": 
            "https://cdn.shopify.com/s/files/1/0960/9930/3717/files/xJoyce_James_5_Stories_from_Dubliners_A_Little_Cloud_Counterparts_Clay_A_Painful_Case_Ivy_Day_in_the_Committee_Room_1914_facsimile_89.jpg?v=1761788882",
        "joyce_james_7_stories_from_dubliners_the_sisters_an_encounter_araby_eveline_after_the_race_two_gallants_the_boarding_house_1914_facsimile_82": 
            "https://cdn.shopify.com/s/files/1/0960/9930/3717/files/xJoyce_James_7_Stories_from_Dubliners_The_Sisters_An_Encounter_Araby_Eveline_After_the_Race_Two_Gallants_The_Boarding_House_1914_facsimile_82.jpg?v=1761788882",
        "joyce_james_dubliners_complete_1914_facsimile_278": 
            "https://cdn.shopify.com/s/files/1/0960/9930/3717/files/xJoyce_James_Dubliners_Complete_1914_facsimile_278.jpg?v=1761788882",

        # Mansfield
        "mansfield_katherine_bliss_and_other_stories_1921_facsimile_287": 
            "https://cdn.shopify.com/s/files/1/0960/9930/3717/files/xMansfield_Katherine_Bliss_and_Other_Stories_1921_facsimile_287.jpg?v=1761788882",
        "mansfield_katherine_prelude_1921_facsimile_77": 
            "https://cdn.shopify.com/s/files/1/0960/9930/3717/files/xMansfield_Katherine_Prelude_1921_facsimile_77.jpg?v=1761788882",
        "mansfield_katherine_seven_stories_from_bliss_1921_facsimile_88": 
            "https://cdn.shopify.com/s/files/1/0960/9930/3717/files/xMansfield_Katherine_Seven_Stories_from_Bliss_1921_facsimile_88.jpg?v=1761788882",
        "mansfield_katherine_six_stories_from_bliss_including_title_story_1921_facsimile_124": 
            "https://cdn.shopify.com/s/files/1/0960/9930/3717/files/xMansfield_Katherine_Six_Stories_from_Bliss_including_Title_Story_1921_facsimile_124.jpg?v=1761788882",

        # Wells
        "wells_hg_2_stories_from_the_collection_t": 
            "https://cdn.shopify.com/s/files/1/0960/9930/3717/files/xWells_HG_2_Stories_from_the_Collection_The_Stolen_Bacillus_and_Three_Others_1895_facsimile_42.jpg?v=1761788882",
        "wells_hg_3_stories_from_the_collection_t": 
            "https://cdn.shopify.com/s/files/1/0960/9930/3717/files/xWells_HG_3_Stories_from_the_Collection_The_Stolen_Bacillus_and_Three_Others_1895_facsimile_65.jpg?v=1761788882",
        "wells_hg_4_stories_from_the_collection_t": 
            "https://cdn.shopify.com/s/files/1/0960/9930/3717/files/xWells_HG_4_Stories_from_the_Collection_The_Stolen_Bacillus_and_Three_Others_1895_facsimile_95.jpg?v=1761788882",
        "wells_hg_9_stories_from_the_collection_t": 
            "https://cdn.shopify.com/s/files/1/0960/9930/3717/files/xWells_HG_9_Stories_from_the_Collection_The_Stolen_Bacillus_1895_facsimile_186.jpg?v=1761788882",

        # Wilde
        "wilde_oscar_lord_arthur_saviles_crime_an": 
            "https://cdn.shopify.com/s/files/1/0960/9930/3717/files/xWilde_Oscar_Lord_Arthur_Saviles_Crime_and_3_Other_Stories_1891_facsimile_163.jpg?v=1761788882",
        "wilde_oscar_five_stories_the_happy_princ": 
            "https://cdn.shopify.com/s/files/1/0960/9930/3717/files/xWilde_Oscar_Five_Stories_The_Happy_Prince_The_Nightingale_and_the_Rose_The_Selfish_Giant_The_Young_King_The_Star_Child_1908_facsimile_118.jpg?v=1761788882",
        "wilde_oscar_four_stories_the_happy_princ": 
            "https://cdn.shopify.com/s/files/1/0960/9930/3717/files/xWilde_Oscar_Four_Stories_The_Happy_Prince_The_Nightingale_and_the_Rose_The_Selfish_Giant_The_Young_King_1908_facsimile_81.jpg?v=1761788882",
        "wilde_oscar_the_happy_prince_1908_facsim": 
            "https://cdn.shopify.com/s/files/1/0960/9930/3717/files/xWilde_Oscar_The_Happy_Prince_1908_facsimile_23.jpg?v=1761788882",
        "wilde_oscar_the_nightingale_and_the_rose": 
            "https://cdn.shopify.com/s/files/1/0960/9930/3717/files/xWilde_Oscar_The_Nightingale_and_the_Rose_1908_facsimile_15.jpg?v=1761788882",
        "wilde_oscar_the_selfish_giant_1908_facsi": 
            "https://cdn.shopify.com/s/files/1/0960/9930/3717/files/xWilde_Oscar_The_Selfish_Giant_1908_facsimile_11.jpg?v=1761788882",
        "wilde_oscar_the_star_child_1908_facsimil": 
            "https://cdn.shopify.com/s/files/1/0960/9930/3717/files/xWilde_Oscar_The_Star_Child_1908_facsimile_37.jpg?v=1761788882",
        "wilde_oscar_the_young_king_1908_facsimil": 
            "https://cdn.shopify.com/s/files/1/0960/9930/3717/files/xWilde_Oscar_The_Young_King_1908_facsimile_32.jpg?v=1761788882",
        "wilde_oscar_three_stories_the_happy_prin": 
            "https://cdn.shopify.com/s/files/1/0960/9930/3717/files/xWilde_Oscar_Three_Stories_The_Happy_Prince_The_Nightingale_and_the_Rose_The_Selfish_Giant_1908_facsimile_49.jpg?v=1761788882",
        "wilde_oscar_two_stories_the_happy_prince": 
            "https://cdn.shopify.com/s/files/1/0960/9930/3717/files/xWilde_Oscar_Two_Stories_The_Happy_Prince_The_Selfish_Giant_1908_facsimile_34.jpg?v=1761788882",

        # Wodehouse
        "wodehouse_pg_11_pg_wodehouse_stories_fea": 
            "https://cdn.shopify.com/s/files/1/0960/9930/3717/files/xWodehouse_PG_11_PG_Wodehouse_Stories_featuring_7_Blandings_stories_and_4_Mr_Mulliner_stories_from_the_volume_Blandings_Castle_1935_facsimile_281.jpg?v=1761788882",
        "wodehouse_pg_2_selected_mr_mulliner_stor": 
            "https://cdn.shopify.com/s/files/1/0960/9930/3717/files/xWodehouse_PG_2_Selected_Mr_Mulliner_Stories_The_Nodder_The_Juice_of_an_Orange_1935_facsimile_45.jpg?v=1761788882",
        "wodehouse_pg_2_wodehouse_blandings_stori": 
            "https://cdn.shopify.com/s/files/1/0960/9930/3717/files/xWodehouse_PG_2_Wodehouse_Blandings_stories_The_Custody_of_the_Pumpkin_Lord_Emsworth_Acts_for_the_Best_1935_facsimile_58.jpg?v=1761788882",
        "wodehouse_pg_3_pg_wodehouse_blandings_st": 
            "https://cdn.shopify.com/s/files/1/0960/9930/3717/files/xWodehouse_PG_3_PG_Wodehouse_Blandings_stories_The_Custody_of_the_Pumpkin_Lord_Emsworth_Acts_for_the_Best_PIG-HOO-O-O-O-EY_1935_facsimile_85.jpg?v=1761788882",
        "wodehouse_pg_4_pg_wodehouse_blandings_st": 
            "https://cdn.shopify.com/s/files/1/0960/9930/3717/files/xWodehouse_PG_4_PG_Wodehouse_Blandings_stories_The_Custody_of_the_Pumpkin_Lord_Emsworth_Acts_for_the_Best_PIG-HOO-O-O-O-EY_Company_for_Gertrude_1935_facsimile_110.jpg?v=1761788882",
        "wodehouse_pg_4_selected_mr_mulliner_stor": 
            "https://cdn.shopify.com/s/files/1/0960/9930/3717/files/xWodehouse_PG_4_Selected_Mr_Mulliner_Stories_The_Nodder_The_Juice_of_an_Orange_The_Rise_of_Minna_Nordstrom_The_Castaways_1935_facsimile_91.jpg?v=1761788882",
        "wodehouse_pg_5_blandings_stories_the_cus": 
            "https://cdn.shopify.com/s/files/1/0960/9930/3717/files/xWodehouse_PG_5_Blandings_stories_The_Custody_of_the_Pumpkin_Lord_Emsworth_Acts_for_the_Best_PIG-HOO-O-O-O-EY_Company_for_Gertrude_The_Go-Getter_1935_facsimile_136.jpg?v=1761788882",
        "wodehouse_pg_7_pg_wodehouse_blandings_st": 
            "https://cdn.shopify.com/s/files/1/0960/9930/3717/files/xWodehouse_PG_7_PG_Wodehouse_Blandings_stories_The_Custody_of_the_Pumpkin_Lord_Emsworth_Acts_for_the_Best_PIG-HOO-O-O-O-EY_and_4_more_1935_facsimile_191.jpg?v=1761788882",

        # Woolf
        "woolf_virginia_a_room_of_ones_own_1935_f": 
            "https://cdn.shopify.com/s/files/1/0960/9930/3717/files/xWoolf_Virginia_A_Room_of_Ones_Own_1935_facsimile_172.jpg?v=1761788882",
        "woolf_virginia_mrs_dalloway_1925_facsimi": 
            "https://cdn.shopify.com/s/files/1/0960/9930/3717/files/xWoolf_Virginia_Mrs_Dalloway_1925_facsimile_296.jpg?v=1761788882"
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
                        # Use Shopify cover (high-res)
                        cover_url = shopify_covers.get(handle, "")

                        eligible.append({
                            "title": title,
                            "handle": handle,
                            "slug": slugify(handle),
                            "grid": layout.get("grid"),
                            "scale": layout.get("scale_pct"),
                            "cover_url": cover_url,  # Shopify cover
                            "pages": pages,
                            "aspect_ratio": aspect_ratio,
                            "page_w": width_cm,
                            "page_h": height_cm,
                            "folder": title.rsplit(" (", 1)[0] + f" ({pages})"
                        })
                except Exception as e:
                    print(f"Skipping row: {e}", flush=True)
        print(f"Loaded {len(eligible)} eligible murals", flush=True)
    except Exception as e:
        print(f"CSV error: {e}", flush=True)

    return eligible