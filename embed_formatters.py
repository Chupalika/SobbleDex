import datetime, pytz
import math
import discord
import settings
import yadon
import constants
import utils

def format_pokemon_embed(name, details):
    dex = int(details["Dex"]) if details["Dex"].isdigit() else 0
    ss = details["SS"].split("/")
    if details["Mega Power"]:
        stats = "**Dex**: {:03d}\n**Type**: {}\n**Icons**: {} ({})\n**MSUs**: {}\n**Mega Effects**: {}".format(
            dex,
            details["Type"],
            details["Icons"],
            int(details["Icons"]) - int(details["MSU"]),
            details["MSU"],
            details["Mega Power"])
    else:
        stats = "**Dex**: {:03d}\n**Type**: {}\n**BP**: {}\n**RMLs**: {}\n**Max AP**: {}\n**Skill**: {}".format(
            dex,
            details["Type"],
            details["BP"],
            details["RML"],
            details["MaxAP"],
            details["Skill"])
        if len(ss) > 0 and ss[0]:
            stats += " ({})".format(", ".join(ss))
    
    the_color = constants.type_colors[details["Type"]] if details["Type"] in constants.type_colors.keys() else discord.Embed.Empty
    embed = discord.Embed(title=name, color=the_color, description=stats)
    embed.set_thumbnail(url="https://raw.githubusercontent.com/Chupalika/Kaleo/icons/Icons/{}.png".format(name.replace("%", "%25").replace(":", "").replace(" ", "%20")))
    return embed

def format_skill_embed(name, details):
    def convert_to_float(f):
        try:
            return float(f)
        except ValueError:
            return 0
    bonus1 = convert_to_float(details["Bonus1"])
    bonus2 = convert_to_float(details["Bonus2"])
    bonus3 = convert_to_float(details["Bonus3"])
    bonus4 = convert_to_float(details["Bonus4"])
    rate1 = int(details["Rate1"]) if details["Rate1"].isdigit() else 0
    rate2 = int(details["Rate2"]) if details["Rate2"].isdigit() else 0
    rate3 = int(details["Rate3"]) if details["Rate3"].isdigit() else 0
    multiplier = convert_to_float(details["Multiplier"])
    sp1 = int(details["SP1"]) if details["SP1"].isdigit() else 0
    sp2 = int(details["SP2"]) if details["SP2"].isdigit() else 0
    sp3 = int(details["SP3"]) if details["SP3"].isdigit() else 0
    sp4 = int(details["SP4"]) if details["SP4"].isdigit() else 0
    notes = yadon.ReadRowFromTable(settings.skill_notes_table, name)
    
    stats = "**Description**: {}\n".format(details["Description"])
    if notes is not None:
        notes = notes[0].replace("\\n", "\n")
        stats += "**Notes**: {}\n".format(utils.emojify(notes))
    stats += "**Activation Rates**: {}% / {}% / {}%\n".format(rate1, rate2, rate3)
    if details["Type"] != "Mega Boost":
        stats += "**Damage Multiplier**: x{:0.2f}\n".format(multiplier)
    if (details["Bonus Effect"] == "Activation Rate"):
        stats += "**SL{} Bonus**: +{:0.0f}% ({:0.0f}% / {:0.0f}% / {:0.0f}%)\n".format(2, bonus1,
                                                                                       min(100, rate1 + bonus1) if rate1 != 0 else 0,
                                                                                       min(100, rate2 + bonus1) if rate2 != 0 else 0,
                                                                                       min(100, rate3 + bonus1) if rate3 != 0 else 0)
        stats += "**SL{} Bonus**: +{:0.0f}% ({:0.0f}% / {:0.0f}% / {:0.0f}%)\n".format(3, bonus2,
                                                                                       min(100, rate1 + bonus2) if rate1 != 0 else 0,
                                                                                       min(100, rate2 + bonus2) if rate2 != 0 else 0,
                                                                                       min(100, rate3 + bonus2) if rate3 != 0 else 0)
        stats += "**SL{} Bonus**: +{:0.0f}% ({:0.0f}% / {:0.0f}% / {:0.0f}%)\n".format(4, bonus3,
                                                                                       min(100, rate1 + bonus3) if rate1 != 0 else 0,
                                                                                       min(100, rate2 + bonus3) if rate2 != 0 else 0,
                                                                                       min(100, rate3 + bonus3) if rate3 != 0 else 0)
        stats += "**SL{} Bonus**: +{:0.0f}% ({:0.0f}% / {:0.0f}% / {:0.0f}%)\n".format(5, bonus4,
                                                                                       min(100, rate1 + bonus4) if rate1 != 0 else 0,
                                                                                       min(100, rate2 + bonus4) if rate2 != 0 else 0,
                                                                                       min(100, rate3 + bonus4) if rate3 != 0 else 0)
    elif (details["Bonus Effect"] == "Multiply Damage"):
        stats += "**SL{} Bonus**: x{:0.2f} (x{:0.2f})\n".format(2, bonus1, multiplier * bonus1)
        stats += "**SL{} Bonus**: x{:0.2f} (x{:0.2f})\n".format(3, bonus2, multiplier * bonus2)
        stats += "**SL{} Bonus**: x{:0.2f} (x{:0.2f})\n".format(4, bonus3, multiplier * bonus3)
        stats += "**SL{} Bonus**: x{:0.2f} (x{:0.2f})\n".format(5, bonus4, multiplier * bonus4)
    elif (details["Bonus Effect"] == "Add Damage"):
        stats += "**SL{} Bonus**: +{:0.2f} (x{:0.2f})\n".format(2, bonus1, multiplier + bonus1)
        stats += "**SL{} Bonus**: +{:0.2f} (x{:0.2f})\n".format(3, bonus2, multiplier + bonus2)
        stats += "**SL{} Bonus**: +{:0.2f} (x{:0.2f})\n".format(4, bonus3, multiplier + bonus3)
        stats += "**SL{} Bonus**: +{:0.2f} (x{:0.2f})\n".format(5, bonus4, multiplier + bonus4)
    stats += "**SP Requirements**: {} => {} => {} => {} (Total: {})\n".format(sp1, sp2 - sp1, sp3 - sp2, sp4 - sp3, sp4)
    
    the_color = constants.skill_colors[details["Type"]] if details["Type"] in constants.skill_colors.keys() else discord.Embed.Empty
    embed = discord.Embed(title=name, color=the_color, description=stats)
    return embed

def format_type_embed(values):
    type, se, nve, weak, res, imm = values
    embed = discord.Embed(title=type, color=constants.type_colors[type])
    embed.add_field(name="Super Effective Against", value=se)
    embed.add_field(name="Not Very Effective Against", value=nve)
    embed.add_field(name="Weaknesses", value=weak)
    embed.add_field(name="Resistances", value=res)
    embed.add_field(name="Status Effect Immunities", value=imm)
    return embed

def format_stage_embed(stage_info, eb_data=("", 0, "", 0), shorthand=False):
    #index, pokemon, hp, hp_mobile, moves, seconds, exp, base_catch, bonus_catch, base_catch_mobile, bonus_catch_mobile, default_supports, s_rank, a_rank, b_rank,num_s_ranks_to_unlock, is_puzzle_stage, extra_hp, layout_index, cost_type, attempt_cost, drop_1_item, drop_1_amount, drop_2_item, drop_2_amount, drop_3_item, drop_3_amount, drop_1_rate, drop_2_rate, drop_3_rate, items, rewards, rewards_UX, cd1, cd2, cd3 = values
    notes = yadon.ReadRowFromTable(settings.stage_notes_table, stage_info["Index"])
    
    if stage_info["Index"].isdigit():
        stage_type = "Main"
        index = stage_info["Index"]
    elif stage_info["Index"].startswith("ex"):
        stage_type = "Expert"
        index = stage_info["Index"][2:]
    elif stage_info["Index"].startswith("s"):
        stage_type = "Event"
        index = stage_info["Index"][1:]
    
    if stage_info["HP_3DS"] != stage_info["HP_Mobile"]:
        stats = "**3DS HP**: {}{}\n**Mobile HP**: {}{}".format(
            stage_info["HP_3DS"],
            " (UX: {})".format(int(stage_info["HP_3DS"]) * 3) if stage_type == "Main" and stage_info["Is_Puzzle_Stage"] != "Puzzle" else "",
            stage_info["HP_Mobile"],
            " (UX: {})".format(int(stage_info["HP_Mobile"]) * 3) if stage_type == "Main" and stage_info["Is_Puzzle_Stage"] != "Puzzle" else "")
    else:
        stats = "**HP**: {}{}{}".format(
            stage_info["HP_3DS"],
            " (UX: {})".format(int(stage_info["HP_3DS"]) * 3) if stage_type == "Main" and stage_info["Is_Puzzle_Stage"] != "Puzzle" else "",
            " + {} ({})".format(stage_info["Extra_HP"], int(stage_info["HP_3DS"]) + (int(stage_info["Extra_HP"]) * eb_data[1])) if stage_info["Extra_HP"] != "0" else "")
    
    if stage_info["Moves_3DS"] != stage_info["Moves_Mobile"]:
        stats += "\n**3DS {}**: {}\n**Mobile {}**: {}".format(
            "Moves" if stage_info["Moves_3DS"] != "0" else "Seconds",
            stage_info["Moves_Mobile"] if stage_info["Moves_Mobile"] != "0" else stage_info["Seconds"],
            "Moves" if stage_info["Moves_Mobile"] != "0" else "Seconds",
            stage_info["Moves_Mobile"] if stage_info["Moves_Mobile"] != "0" else stage_info["Seconds"],)
    else:
        stats += "\n**{}**: {}".format(
            "Moves" if stage_info["Moves_3DS"] != "0" else "Seconds",
            stage_info["Moves_3DS"] if stage_info["Moves_3DS"] != "0" else stage_info["Seconds"])
    
    if int(stage_info["HP_3DS"]) > 1 and stage_info["Is_Puzzle_Stage"] != "Puzzle":
        real_hp_3ds = int(stage_info["HP_3DS"]) if stage_info["Extra_HP"] == "0" else int(stage_info["HP_3DS"]) + int(stage_info["Extra_HP"]) * eb_data[1]
        real_hp_mobile = int(stage_info["HP_Mobile"]) if stage_info["Extra_HP"] == "0" else int(stage_info["HP_Mobile"]) + int(stage_info["Extra_HP"]) * eb_data[1]
        if stage_info["Moves_Mobile"] != "0":
            dpm_3ds = math.ceil(real_hp_3ds / int(stage_info["Moves_3DS"]))
            dpm_mobile = math.ceil(real_hp_mobile / int(stage_info["Moves_Mobile"]))
            if dpm_3ds != dpm_mobile:
                stats += f"\n**Damage/move (3DS)**: {dpm_3ds}"
                if "M+5" in stage_info["Items"]:
                    dpm_m5 = math.ceil(real_hp_3ds / (int(stage_info["Moves_3DS"]) + 5))
                    stats += utils.emojify(f" ([M+5] {dpm_m5})")
                stats += f"\n**Damage/move (Mobile)**: {dpm_mobile}"
                if "M+5" in stage_info["Items"]:
                    dpm_m5 = math.ceil(real_hp_mobile / (int(stage_info["Moves_Mobile"]) + 5))
                    stats += utils.emojify(f" ([M+5] {dpm_m5})")
            else:
                stats += f"\n**Damage/move**: {dpm_3ds}"
                if "M+5" in stage_info["Items"]:
                    dpm_m5 = math.ceil(real_hp_3ds / (int(stage_info["Moves_3DS"]) + 5))
                    stats += utils.emojify(f" ([M+5] {dpm_m5})")
        
        else:
            #assumes 3ds and mobile hp are the same for timed stages
            dps = math.ceil(real_hp_3ds / int(stage_info["Seconds"]))
            stats += f"\n**Damage/second**: {dps}"
            if "T+10" in stage_info["Items"]:
                dps_t10 = math.ceil(real_hp_3ds / (int(stage_info["Seconds"]) + 10))
                stats += utils.emojify(f" ([T+10] {dps_t10})")
    
    if stage_info["EXP_3DS"] != stage_info["EXP_Mobile"]:
        stats += "\n**Experience (3DS)**: {}\n**Experience (Mobile)**: {}".format(stage_info["EXP_3DS"], stage_info["EXP_Mobile"])
    else:
        stats += "\n**Experience**: {}".format(stage_info["EXP_3DS"])
    
    if eb_data[3] == 0:
        if stage_info["Base_Catch_3DS"] != stage_info["Base_Catch_Mobile"] or stage_info["Bonus_Catch_3DS"] != stage_info["Bonus_Catch_Mobile"]:
            stats += "\n**Catchability (3DS)**: {}% + {}%/{}".format(
                stage_info["Base_Catch_3DS"],
                stage_info["Bonus_Catch_3DS"],
                "move" if stage_info["Moves_3DS"] != "0" else "3sec")
            stats += "\n**Catchability (Mobile)**: {}% + {}%/{}".format(
                stage_info["Base_Catch_Mobile"],
                stage_info["Bonus_Catch_Mobile"],
                "move" if stage_info["Moves_Mobile"] != "0" else "3sec")
        else:
            stats += "\n**Catchability**: {}% + {}%/{}".format(
                stage_info["Base_Catch_3DS"],
                stage_info["Bonus_Catch_3DS"],
                "move" if stage_info["Moves_3DS"] != "0" else "3sec")
    else:
        stats += "\n**Catchability**: {}%".format(min(eb_data[3], 100))
    default_supports = stage_info["Default_Supports"].split("/")
    if len(default_supports) > 4:
        num_extra = len(default_supports) - 4
        stats += "\n**Default Supports**: {} | {}".format(
            utils.emojify("".join(["[{}]".format(p) for p in default_supports[0:num_extra]])),
            utils.emojify("".join(["[{}]".format(p) for p in default_supports[num_extra:]])))
    else:
        stats += "\n**Default Supports**: {}".format(utils.emojify("".join(["[{}]".format(p) for p in default_supports])))
    stats += "\n**Rank Requirements**: {} / {} / {}".format(stage_info["S_Rank_Moves"], stage_info["A_Rank_Moves"], stage_info["B_Rank_Moves"])
    if stage_type == "Expert":
        stats += "\n**S-Ranks to unlock**: {}".format(stage_info["Num_S_Ranks_To_Unlock"])
    stats += "\n**Attempt Cost**: {} x{}".format(utils.emojify("[{}]".format(stage_info["Attempt_Cost_Type"])), stage_info["Attempt_Cost_Amount"])
    if stage_info["Drop_1_Item"] != "Nothing" or stage_info["Drop_2_Item"] != "Nothing" or stage_info["Drop_3_Item"] != "Nothing":
        stats += "\n**Drop Items**: {}{} / {}{} / {}{}\n**Drop Rates**: {}% / {}% / {}%".format(
            utils.emojify("[{}]".format(stage_info["Drop_1_Item"])),
            " x{}".format(stage_info["Drop_1_Amount"]) if stage_info["Drop_1_Amount"] != "1" else "",
            utils.emojify("[{}]".format(stage_info["Drop_2_Item"])),
            " x{}".format(stage_info["Drop_2_Amount"]) if stage_info["Drop_2_Amount"] != "1" else "",
            utils.emojify("[{}]".format(stage_info["Drop_3_Item"])),
            " x{}".format(stage_info["Drop_3_Amount"]) if stage_info["Drop_3_Amount"] != "1" else "",
            stage_info["Drop_1_Rate"],
            stage_info["Drop_2_Rate"],
            stage_info["Drop_3_Rate"])
    items = stage_info["Items"].split("/")
    #auto remove c-1 if less than 4 supports
    if len(default_supports) < 4 and "C-1" in items:
        items.remove("C-1")
    stats += "\n**Items**: {}".format(utils.emojify("".join(["[{}]".format(item) for item in items])))
    if stage_info["Rewards"] != "Nothing":
        stats += "\n**Initial clear reward**: {}".format(utils.emojify(stage_info["Rewards"]))
    if stage_info["Rewards_UX"] != "Nothing":
        stats += "\n**UX Initial clear reward**: {}".format(utils.emojify(stage_info["Rewards_UX"]))
    if eb_data[2]:
        stats += "\n**EB stage clear reward**: {}".format(utils.emojify(eb_data[2]))
    if notes is not None:
        stats += "\n**Notes**: {}".format(utils.emojify(notes[0]).replace("\\n", "\n"))
    
    header = "{} Stage {}: {}{}{}".format(stage_type, index, stage_info["Pokemon"], " " + utils.emojify("[{}]".format(stage_info["Pokemon"])), eb_data[0])
    type = yadon.ReadRowFromTable(settings.pokemon_table, stage_info["Pokemon"], named_columns=True)["Type"]
    embed = discord.Embed(title=header, color=constants.type_colors[type], description=stats)
    if not shorthand:
        if stage_info["Layout_Index"] != "0":
            embed.set_thumbnail(url="https://raw.githubusercontent.com/Chupalika/Kaleo/icons/{} Stages Layouts/Layout Index {}.png".format(stage_type, stage_info["Layout_Index"]).replace(" ", "%20"))
            embed.url = "https://raw.githubusercontent.com/Chupalika/Kaleo/icons/{} Stages Layouts/Layout Index {}.png".format(stage_type, stage_info["Layout_Index"]).replace(" ", "%20")
        if stage_info["Countdown_1"] != "Nothing":
            embed.add_field(name="**Countdown 1**", value=utils.emojify(stage_info["Countdown_1"].replace("\\n", "\n")), inline=False)
        if stage_info["Countdown_2"] != "Nothing":
            embed.add_field(name="**Countdown 2**", value=utils.emojify(stage_info["Countdown_2"].replace("\\n", "\n")), inline=False)
        if stage_info["Countdown_3"] != "Nothing":
            embed.add_field(name="**Countdown 3**", value=utils.emojify(stage_info["Countdown_3"].replace("\\n", "\n")), inline=False)
    return embed

def format_starting_board_embed(stage_info):
    #index, pokemon, _, _, _, _, _, _, _, _, _, _, _, _, _, _, _, _, layout_index, _, _, _, _, _, _, _, _, _, _, _, _, _, _, _, _, _ = values
    
    if stage_info["Index"].isdigit():
        stage_type = "Main"
        index = stage_info["Index"]
    elif stage_info["Index"].startswith("ex"):
        stage_type = "Expert"
        index = stage_info["Index"][2:]
    elif stage_info["Index"].startswith("s"):
        stage_type = "Event"
        index = stage_info["Index"][1:]
    
    header = "{} Stage {}: {} {}".format(stage_type, index, stage_info["Pokemon"], utils.emojify("[{}]".format(stage_info["Pokemon"])))
    type = yadon.ReadRowFromTable(settings.pokemon_table, stage_info["Pokemon"], named_columns=True)["Type"]
    embed = discord.Embed(title=header, color=constants.type_colors[type])
    if stage_info["Layout_Index"] != "0":
        embed.set_image(url="https://raw.githubusercontent.com/Chupalika/Kaleo/icons/{} Stages Layouts/Layout Index {}.png".format(stage_type, stage_info["Layout_Index"]).replace(" ", "%20"))
    else:
        embed.description = "No initial board layout"
    return embed

def format_event_embed(values):
    index, stage_type, event_pokemon, _, repeat_type, repeat_param_1, repeat_param_2, start_time, end_time, duration_string, cost_string, attempts_string, encounter_rates = values
    
    event_pokemon = event_pokemon.split("/")
    encounter_rates = encounter_rates.split("/")
    cost_string = "" if cost_string == "Nothing" else cost_string
    attempts_string = "" if attempts_string == "Nothing" else attempts_string

    event_pokemon_string = ""
    if stage_type == "Daily":
        header = "Daily Pokémon"
        for i in range(len(event_pokemon)):
            event_pokemon_string += "{}: {} [{}]\n".format(["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"][(i+1)%7], event_pokemon[i], event_pokemon[i])
    elif stage_type == "Escalation":
        header = "Escalation Battles: {} [{}]".format(event_pokemon[0], event_pokemon[0])
    elif stage_type == "Safari":
        header = "Pokémon Safari"
        for i in range(len(event_pokemon) - 1):
            #For some reason the first pokemon is duplicated here
            event_pokemon_string += "[{}] {} ({}%)\n".format(event_pokemon[i+1], event_pokemon[i+1], encounter_rates[i])
    elif stage_type == "Monthly":
        header = "Monthly Challenge"
        for i in range(len(event_pokemon)):
            event_pokemon_string += "[{}] {} ({}%)\n".format(event_pokemon[i], event_pokemon[i], encounter_rates[i])
    else:
        header = "{} [{}]".format(event_pokemon[0], event_pokemon[0])
    
    date_header = "{} Event".format(repeat_type)
    if repeat_type == "Rotation":
        date_header += ": Week {}/24".format(int(repeat_param_1) + 1)
    
    starts_when = None
    ends_when = None
    if repeat_type != "Weekly":
        st = start_time.split("/")
        et = end_time.split("/")
        if repeat_type == "Rotation":
            start_time = datetime.datetime(int(st[0]), int(st[1]), int(st[2]), int(st[3]), int(st[4]), tzinfo=pytz.utc)
            end_time = datetime.datetime(int(et[0]), int(et[1]), int(et[2]), int(et[3]), int(et[4]), tzinfo=pytz.utc)
            while end_time < datetime.datetime.now(tz=pytz.utc):
                start_time = start_time + datetime.timedelta(168)
                end_time = end_time + datetime.timedelta(168)
            starts_when = start_time - datetime.datetime.now(tz=pytz.utc)
            ends_when = end_time - datetime.datetime.now(tz=pytz.utc)
            start_time = start_time.strftime("%Y/%m/%d %H:%M UTC")
            end_time = end_time.strftime("%Y/%m/%d %H:%M UTC")
        else:
            start_time = "{}/{}/{} {}:{} UTC".format(st[0], st[1], st[2], st[3], st[4])
            end_time = "{}/{}/{} {}:{} UTC".format(et[0], et[1], et[2], et[3], et[4])
            if repeat_type == "Monthly":
                add_one_month = 1 if datetime.datetime.now(tz=pytz.utc).day >= int(et[2]) else 0
                add_one_year = 1 if datetime.datetime.now(tz=pytz.utc).month == 12 and datetime.datetime.now(tz=pytz.utc).day >= int(et[2]) else 0
                st[0] = datetime.datetime.now(tz=pytz.utc).year + add_one_year
                et[0] = datetime.datetime.now(tz=pytz.utc).year + add_one_year
                st[1] = datetime.datetime.now(tz=pytz.utc).month + add_one_month
                et[1] = datetime.datetime.now(tz=pytz.utc).month + add_one_month
            elif repeat_type == "Yearly":
                add_one_year = 1 if datetime.datetime.now(tz=pytz.utc).month >= int(et[1]) and datetime.datetime.now(tz=pytz.utc).day >= int(et[2]) else 0
                st[0] = datetime.datetime.now(tz=pytz.utc).year + add_one_year
                et[0] = datetime.datetime.now(tz=pytz.utc).year + add_one_year
            start_time_2 = datetime.datetime(int(st[0]), int(st[1]), int(st[2]), int(st[3]), int(st[4]), tzinfo=pytz.utc)
            end_time_2 = datetime.datetime(int(et[0]), int(et[1]), int(et[2]), int(et[3]), int(et[4]), tzinfo=pytz.utc)
            starts_when = start_time_2 - datetime.datetime.now(tz=pytz.utc)
            ends_when = end_time_2 - datetime.datetime.now(tz=pytz.utc)
    
    embed = discord.Embed(title=utils.emojify(header), color=constants.event_type_colors[stage_type])
    if event_pokemon_string:
        embed.add_field(name="Event Pokémon", value=utils.emojify(event_pokemon_string), inline=False)
    if starts_when and starts_when > datetime.timedelta():
        event_duration_string = "{} to {} ({}) (starts in {} days {} hours)".format(start_time, end_time, duration_string, starts_when.days, int(starts_when.seconds / 3600))
    elif ends_when and ends_when > datetime.timedelta():
        event_duration_string = "{} to {} ({}) (ends in {} days {} hours)".format(start_time, end_time, duration_string, ends_when.days, int(ends_when.seconds / 3600))
    else:
        event_duration_string = "{} to {} ({})".format(start_time, end_time, duration_string)
    embed.add_field(name=date_header, value="Event duration: {}".format(event_duration_string), inline=False)
    if cost_string != "" or attempts_string != "":
        embed.add_field(name="Misc. Details", value=utils.emojify(cost_string + "\n" + attempts_string), inline=False)
    return embed

def format_eb_rewards_embed(values):
    pokemon = values[0]
    rewards = values[1:]
    
    stats = ""
    for entry in rewards:
        level, reward_item, reward_amount = entry.split("/")
        stats += "Level {} reward: {} x{}\n".format(level, utils.emojify("[{}]".format(reward_item)), reward_amount)
    stats = stats[:-1]
    
    embed = discord.Embed(title="{} Escalation Battles Rewards".format(pokemon), color=0x4e7e4e, description=stats)
    return embed

def format_eb_details_embed(values):
    pokemon_name = values[0]
    level_sets = values[1:]
    
    stats = ""
    for levelset in level_sets:
        start_level, end_level, stage_index = levelset.split("/")
        stage_info = yadon.ReadRowFromTable(settings.event_stages_table, stage_index, named_columns=True)
        
        if end_level == "-1":
            levels = "**Levels {}+**".format(start_level)
        elif int(start_level) == int(end_level) - 1:
            levels = "**Level {}**".format(start_level)
        else:
            levels = "**Levels {} to {}**".format(start_level, int(end_level) - 1)
        
        extra = ""
        default_supports = stage_info["Default_Supports"].split("/")
        if len(default_supports) == 3:
            extra = " **(3 supports)**"
        elif len(default_supports) == 5:
            extra = utils.emojify(" **(5th support: [{}])**".format(default_supports[0]))
        
        stats += "{}: {}{} / {}{}\n".format(levels, stage_info["HP_Mobile"], " + {}".format(stage_info["Extra_HP"]) if stage_info["Extra_HP"] != "0" else "", stage_info["Seconds"] if stage_info["Seconds"] != "0" else stage_info["Moves_Mobile"], extra)
    
    embed = discord.Embed(title="{} Escalation Battles Details".format(pokemon_name), color=0x4e7e4e, description=stats)
    return embed

def format_week_embed(query_week):
    comp = ""
    daily = ""
    oad = ""
    gc = ""
    eb = ""
    safari = ""
    
    events = yadon.ReadTable(settings.events_table)
    for index, values in events.items():
        stage_type, event_pokemon, stage_indices, repeat_type, repeat_param_1, repeat_param_2, start_time, end_time, duration, cost_string, _, encounter_rates = values
        if repeat_type != "Rotation" or not (int(repeat_param_1)+1 == query_week or (duration == "14 days" and int(repeat_param_1)+2 == query_week)):
            continue
        
        event_pokemon = event_pokemon.split("/")
        stage_info = yadon.ReadRowFromTable(settings.event_stages_table, stage_indices.split("/")[0], named_columns=True)
        #_, _, _, _, _, _, _, _, _, _, _, _, _, _, _, _, _, _, cost_type, attempt_cost, drop_1_item, drop_1_amount, drop_2_item, drop_2_amount, drop_3_item, drop_3_amount, drop_1_rate, drop_2_rate, drop_3_rate, items, _, _, _, _, _ = stage_values
        
        drops_string = ""
        attempt_cost_string = ""
        unlock_cost_string = ""
        if stage_info["Drop_1_Item"] != "Nothing" or stage_info["Drop_2_Item"] != "Nothing" or stage_info["Drop_3_Item"] != "Nothing":
            #need to add this because sometimes it goes over the character limit...
            if stage_info["Drop_1_Item"] == stage_info["Drop_2_Item"] == stage_info["Drop_3_Item"] and stage_info["Drop_1_Amount"] == stage_info["Drop_2_Amount"] == stage_info["Drop_3_Amount"]:
                drops_string += " [{}{} {}% / {}% / {}%]".format(
                    utils.emojify("[{}]".format(stage_info["Drop_1_Item"])),
                    " x{}".format(stage_info["Drop_1_Amount"]) if stage_info["Drop_1_Amount"] != "1" else "",
                    stage_info["Drop_1_Rate"],
                    stage_info["Drop_2_Rate"],
                    stage_info["Drop_3_Rate"])
            else:
                drops_string += " [{}{} {}% / {}{} {}% / {}{} {}%]".format(
                    utils.emojify("[{}]".format(stage_info["Drop_1_Item"])),
                    " x{}".format(stage_info["Drop_1_Amount"]) if stage_info["Drop_1_Amount"] != "1" else "",
                    stage_info["Drop_1_Rate"],
                    utils.emojify("[{}]".format(stage_info["Drop_2_Item"])),
                    " x{}".format(stage_info["Drop_2_Amount"]) if stage_info["Drop_2_Amount"] != "1" else "",
                    stage_info["Drop_2_Rate"],
                    utils.emojify("[{}]".format(stage_info["Drop_3_Item"])),
                    " x{}".format(stage_info["Drop_3_Amount"]) if stage_info["Drop_3_Amount"] != "1" else "",
                    stage_info["Drop_3_Rate"])
        if stage_info["Attempt_Cost_Amount"] != "1" or stage_info["Attempt_Cost_Type"] != "Heart":
            attempt_cost_string += " ({} x{})".format(utils.emojify("[{}]".format(stage_info["Attempt_Cost_Type"])), stage_info["Attempt_Cost_Amount"])
        if cost_string != "Nothing":
            unlock_cost_string += " ({} {})".format(utils.emojify(cost_string.split(" ")[1]), cost_string.split(" ")[2])
        
        #Challenge
        if stage_type == "Challenge":
            gc += "- {}{}{}{}\n".format(utils.emojify("[{}]".format(event_pokemon[0])), drops_string, attempt_cost_string, unlock_cost_string)
        #Daily
        if stage_type == "Daily":
            event_pokemon = utils.remove_duplicates(event_pokemon)
            if len(event_pokemon) == 1:
                oad += "- {}{}{}".format(utils.emojify("[{}]".format(event_pokemon[0])), drops_string, attempt_cost_string)
            else:
                daily += "- "
                for pokemon in event_pokemon:
                    daily += utils.emojify("[{}]".format(pokemon))
                daily += drops_string
        #Competition
        if stage_type == "Competitive":
            #There are duplicate entries... grab only one of them
            if comp == "":
                items_string = ""
                for item in stage_info["Items"].split("/"):
                    items_string += utils.emojify("[{}]".format(item))
                comp += "- {} ({})".format(utils.emojify("[{}]".format(event_pokemon[0])), items_string)
        #EB
        if stage_type == "Escalation":
            eb += "- {}{}".format(utils.emojify("[{}]".format(event_pokemon[0])), drops_string)
        #Safari
        if stage_type == "Safari":
            #For some reason the first pokemon is duplicated here
            event_pokemon = event_pokemon[1:]
            encounter_rates = encounter_rates.split("/")
            safari += "- "
            for j in range(len(event_pokemon)):
                safari += "{} ({}%), ".format(utils.emojify("[{}]".format(event_pokemon[j])), encounter_rates[j])
            safari = safari[:-2]
            safari += drops_string
    
    embed = discord.Embed(title="Event Rotation Week {}".format(query_week), color=0xff0000)
    if comp != "":
        embed.add_field(name="Competitive Stage", value=comp, inline=False)
    embed.add_field(name="Challenges", value=gc, inline=False)
    if eb != "":
        embed.add_field(name="Escalation Battles", value=eb, inline=False)
    if safari != "":
        embed.add_field(name="Safari", value=safari, inline=False)
    embed.add_field(name="One Chance a Day!", value=oad, inline=False)
    embed.add_field(name="Daily", value=daily, inline=False)
    
    return embed

def format_query_results_embed(header, buckets, use_emojis):
    embed = discord.Embed(description=header)
    
    for bucket_key in buckets.keys():
        output_string = ""
        for item in buckets[bucket_key]:
            if use_emojis:
                try:
                    #surround ss pokemon with parentheses (instead of boldifying it, because, y'know... can't boldify emojis)
                    if item.find("**") != -1:
                        output_string += "([{}])".format(item[:-2])
                    else:
                        output_string += "[{}]".format(item)
                except KeyError:
                    output_string += "{} ".format("**" + item if item.find("**") != -1 else item)
            else:
                output_string += "{}, ".format("**" + item if item.find("**") != -1 else item)
        if not use_emojis:
            output_string = output_string[:-2]
        else:
            output_string = utils.emojify(output_string)
        embed.add_field(name=bucket_key, value=output_string, inline=False)
    
    return embed

def format_guides_embed(guides, page=0):
    embed = discord.Embed()
    return embed