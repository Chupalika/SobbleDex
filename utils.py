import re, difflib, asyncio
import datetime, pytz
import discord
import settings, constants
import yadon

emojis = {}

def alias(query):
    aliases = {k.lower():v[0] for k,v in yadon.ReadTable(settings.aliases_table).items()}
    try:
        return aliases[query.lower()]
    except KeyError:
        return query

def strip_punctuation(string):
    return string.replace(" ", "").replace("(", "").replace(")", "").replace("-", "").replace("'", "").replace("é", "e").replace(".", "").replace("%", "").replace("+", "").replace(":", "").replace("#", "")

def remove_duplicates(list):
    ans = []
    for item in list:
        if item not in ans:
            ans.append(item)
    return ans

def emojify(the_message, check_aliases=False):
    emojified_message = the_message
    
    possible_emojis = re.findall(r"\[[^\[\]]*\]", the_message)
    possible_emojis = remove_duplicates(possible_emojis)
    
    #for each of the strings that were in []
    for i in range(len(possible_emojis)):
        raw = possible_emojis[i][1:-1]
        #figure out the string that is trying to be emojified
        if check_aliases:
            try:
                emoji_name = alias(raw)
            except:
                emoji_name = raw
        else:
            emoji_name = raw
        #replace it with the emoji if it exists
        try:
            emojified_message = emojified_message.replace("[{}]".format(raw), emojis[strip_punctuation(emoji_name.lower())])
        except KeyError:
            emojified_message = emojified_message.replace("[{}]".format(raw), raw)
    
    return emojified_message

def get_current_week():
    er_start_time = datetime.datetime(settings.er_start_year, settings.er_start_month, settings.er_start_day, settings.er_start_hour, tzinfo=pytz.utc)
    current_time = datetime.datetime.now(tz=pytz.utc)
    td = current_time - er_start_time
    query_week = ((td.days // 7) % 24) + 1
    return query_week

def current_eb_pokemon():
    query_week = get_current_week()
    events = yadon.ReadTable(settings.events_table)
    for index, values in events.items():
        stage_type, event_pokemon, _, repeat_type, repeat_param_1, _, _, _, duration_string, _, _, _ = values
        event_week = int(repeat_param_1) + 1
        #assumes EBs are either 1 week or 2 weeks
        event_week_2 = event_week + 1 if duration_string == "14 days" else event_week
        if stage_type == "Escalation" and repeat_type == "Rotation" and (event_week == query_week or event_week_2 == query_week):
            return event_pokemon
    return None

def current_comp_pokemon():
    query_week = get_current_week()
    events = yadon.ReadTable(settings.events_table)
    for index, values in events.items():
        stage_type, event_pokemon, _, repeat_type, repeat_param_1, _, _, _, duration_string, _, _, _ = values
        event_week = int(repeat_param_1) + 1
        if stage_type == "Competitive" and repeat_type == "Rotation" and (event_week == query_week):
            return event_pokemon
    return None

#fetches today's event pokemon based on start date (meaning it will not return pokemon that started before today)
def get_current_event_pokemon():
    today = datetime.datetime.now(tz=pytz.utc)
    ans = []
    for k,v in yadon.ReadTable(settings.events_table).items():
        stage_type, event_pokemon, stage_indices, repeat_type, repeat_param_1, repeat_param_2, start_time, end_time, duration_string, cost_string, attempts_string, encounter_rates = v
        if repeat_type == "Weekly" and today.weekday() == int(repeat_param_1):
            ans += event_pokemon.split("/")
        elif repeat_type == "Monthly" and today.day == int(repeat_param_1):
            ans += event_pokemon.split("/")
        elif repeat_type == "Yearly" and today.month == int(repeat_param_1):
            #assuming all yearly events are daily stage type
            event_start_date = datetime.datetime(today.year, int(repeat_param_1), int(repeat_param_2), tzinfo=pytz.utc)
            #assuming the format "3 days"
            duration = int(duration_string.split(" ")[0])
            td = today - event_start_date
            if (td.days >= 0 and td.days < duration):
                ans.append(event_pokemon.split("/")[td.days])
        elif repeat_type == "Rotation":
            st = start_time.split("/")
            et = end_time.split("/")
            start_time = datetime.datetime(int(st[0]), int(st[1]), int(st[2]), int(st[3]), int(st[4]), tzinfo=pytz.utc)
            end_time = datetime.datetime(int(et[0]), int(et[1]), int(et[2]), int(et[3]), int(et[4]), tzinfo=pytz.utc)
            while end_time < datetime.datetime.now(tz=pytz.utc):
                start_time = start_time + datetime.timedelta(168)
                end_time = end_time + datetime.timedelta(168)
            
            if stage_type == "Daily":
                duration = int(duration_string.split(" ")[0])
                td = today - start_time
                if (td.days >= 0 and td.days < duration):
                    try:
                        ans.append(event_pokemon.split("/")[(td.days + 1) % 7])
                    except IndexError:
                        pass
            elif today.year == start_time.year and today.month == start_time.month and today.day == start_time.day and event_pokemon not in ans:
                ans += event_pokemon.split("/")
    return ans

def get_farmable_pokemon():
    farmable_pokemon = []
    
    main_stages = yadon.ReadTable(settings.main_stages_table)
    for main_stage in main_stages.values():
        drops = [main_stage[20], main_stage[22], main_stage[24]]
        if "PSB" in drops:
            farmable_pokemon.append(main_stage[0])
    
    expert_stages = yadon.ReadTable(settings.expert_stages_table)
    for expert_stage in expert_stages.values():
        drops = [expert_stage[20], expert_stage[22], expert_stage[24]]
        if "PSB" in drops:
            farmable_pokemon.append(expert_stage[0])
    
    event_stages = yadon.ReadTable(settings.event_stages_table)
    for event_stage in event_stages.values():
        drops = [event_stage[20], event_stage[22], event_stage[24]]
        if "PSB" in drops:
            farmable_pokemon.append(event_stage[0])
    
    return farmable_pokemon

#Look up a queried Pokemon to see if it exists as an alias (and/or in an additionally provided list), provide some suggestions to the user if it doesn't, and return the corrected query, otherwise None
async def pokemon_lookup(context, query=None, enable_dym=True, skill_lookup=False, *args, **kwargs):
    if query is None:
        query = args[0]
    
    aliases = {k.lower():v[0] for k,v in yadon.ReadTable(settings.aliases_table).items()}
    try:
        query = aliases[query.lower()]
    except KeyError:
        pass
    
    pokemon_dict = {k.lower():k for k in yadon.ReadTable(settings.pokemon_table, named_columns=True).keys()}
    skill_dict = {k.lower():k for k in yadon.ReadTable(settings.skills_table, named_columns=True).keys()}
    #get properly capitalized name
    try:
        if skill_lookup:
            query = skill_dict[query.lower()]
        else:
            query = pokemon_dict[query.lower()]
    except KeyError:
        pass
    
    if (not skill_lookup and query.lower() not in pokemon_dict.keys()) or (skill_lookup and query.lower() not in skill_dict.keys()):
        if not enable_dym:
            return
        
        if skill_lookup:
            add = skill_dict.values()
        else:
            add = pokemon_dict.values()
        
        close_matches = difflib.get_close_matches(query, list(aliases.keys()) + list(add), n=settings.dym_limit, cutoff=settings.dym_threshold)
        if len(close_matches) == 0:
            await context.koduck.send_message(receive_message=context.message, content=settings.message_pokemon_lookup_no_result.format("Skill" if skill_lookup else "Pokemon", query))
            return
        
        choices = []
        no_duplicates = []
        for close_match in close_matches:
            try:
                if aliases[close_match].lower() not in no_duplicates:
                    choices.append((close_match, aliases[close_match]))
                    no_duplicates.append(aliases[close_match].lower())
            except KeyError:
                if close_match.lower() not in no_duplicates:
                    choices.append((close_match, close_match))
                    no_duplicates.append(close_match.lower())
        
        output_string = ""
        for i in range(len(choices)):
            output_string += "\n{} {}".format(constants.number_emojis[i+1], choices[i][0] if choices[i][0] == choices[i][1] else "{} ({})".format(choices[i][0], choices[i][1]))
        result = await choice_react(context, len(choices), settings.message_pokemon_lookup_no_result.format("Skill" if skill_lookup else "Pokemon", query) + "\n" + settings.message_pokemon_lookup_suggest + output_string)
        if result is None:
            return
        else:
            choice = choices[result][1]
            if skill_lookup:
                return skill_dict.get(choice.lower(), choice)
            else:
                return pokemon_dict.get(choice.lower(), choice)
    
    else:
        return query

async def choice_react(context, num_choices, question_string):
    #there are only 9 (10) number emojis :(
    num_choices = min(num_choices, 9)
    num_choices = min(num_choices, settings.choice_react_limit)
    the_message = await context.koduck.send_message(receive_message=context.message, content=question_string)
    choice_emojis = constants.number_emojis[:num_choices+1]
    
    #add reactions
    for i in range(len(choice_emojis)):
        await the_message.add_reaction(choice_emojis[i])
    
    #wait for reaction (with timeout)
    def check(reaction, user):
        return reaction.message.id == the_message.id and user == context.message.author and str(reaction.emoji) in choice_emojis
    try:
        reaction, _ = await context.koduck.client.wait_for('reaction_add', timeout=settings.dym_timeout, check=check)
    except asyncio.TimeoutError:
        reaction = None
    
    #remove reactions
    for i in range(len(choice_emojis)):
        try:
            await the_message.remove_reaction(choice_emojis[i], context.koduck.client.user)
        except discord.errors.NotFound:
            break
    
    #return the chosen answer if there was one
    if reaction is None:
        return
    result_emoji = reaction.emoji
    choice = choice_emojis.index(result_emoji)
    if choice == 0:
        return
    else:
        return choice-1