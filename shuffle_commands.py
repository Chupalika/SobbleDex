import datetime, pytz, difflib, re
from typing import Any
from math import floor
from collections import OrderedDict
import discord
import asyncio
from koduck import KoduckContext
from models import QueryType, UserQuery
import settings
import yadon
import constants
import utils
import embed_formatters

async def update_emojis(context, *args, **kwargs):
    utils.emojis = {}
    for server in context.koduck.client.guilds:
        if server.name.startswith("Pokemon Shuffle Icons") or server.id == settings.main_server_id:
            for emoji in server.emojis:
                utils.emojis[emoji.name.lower()] = "<:{}:{}>".format(emoji.name, emoji.id)

async def emojify_2(context, *args, **kwargs):
    emojified_message = utils.emojify(context.param_line, check_aliases=True)
    if emojified_message:
        return await context.koduck.send_message(receive_message=context.message, content=emojified_message)

async def add_alias(context, *args, **kwargs):
    if len(args) < 2:
        return await context.koduck.send_message(receive_message=context.message, content=settings.message_add_alias_no_param)
    if len(args) > settings.manage_alias_limit + 1:
        return await context.koduck.send_message(receive_message=context.message, content=settings.message_add_alias_too_many_params.format(settings.manage_alias_limit))
    
    #parse params
    aliases = {k.lower():v[0] for k,v in yadon.ReadTable(settings.aliases_table).items()}
    try:
        original = aliases[args[0].lower()]
    except KeyError:
        original = args[0]
    
    #action
    succeeded = []
    failed = []
    failed2 = []
    failed3 = []
    for alias in args[1:]:
        if alias.lower() in aliases.keys():
            failed.append(alias)
        elif re.findall(r"<@!?[0-9]*>", alias):
            failed3.append(alias)
        else:
            try:
                yadon.AppendRowToTable(settings.aliases_table, alias, [original])
                succeeded.append(alias)
            except OSError:
                failed2.append(alias)
    
    return_message = ""
    for s in succeeded:
        return_message += settings.message_add_alias_success.format(original, s) + "\n"
    for f in failed:
        return_message += settings.message_add_alias_failed.format(f, aliases[f.lower()]) + "\n"
    for f in failed2:
        return_message += settings.message_add_alias_failed_2.format(f) + "\n"
    for f in failed3:
        return_message += settings.message_add_alias_failed_3.format(f) + "\n"
    
    return await context.koduck.send_message(receive_message=context.message, content=return_message)

async def remove_alias(context, *args, **kwargs):
    if len(args) < 1:
        return await context.koduck.send_message(receive_message=context.message, content=settings.message_remove_alias_no_param)
    if len(args) > settings.manage_alias_limit:
        return await context.koduck.send_message(receive_message=context.message, content=settings.message_remove_alias_too_many_params.format(settings.manage_alias_limit))
    
    aliases = {k.lower():v[0] for k,v in yadon.ReadTable(settings.aliases_table).items()}
    helper = {k.lower():k for k in yadon.ReadTable(settings.aliases_table).keys()}
    
    succeeded = []
    failed = []
    failed2 = []
    for alias in args:
        if alias.lower() not in aliases.keys():
            failed.append(alias)
        else:
            original = aliases[alias.lower()]
            try:
                yadon.RemoveRowFromTable(settings.aliases_table, helper[alias.lower()])
                succeeded.append((original, alias))
            except OSError:
                failed2.append(alias)
    
    return_message = ""
    for s in succeeded:
        return_message += settings.message_remove_alias_success.format(s[0], s[1]) + "\n"
    for f in failed:
        return_message += settings.message_remove_alias_failed.format(f) + "\n"
    for f in failed2:
        return_message += settings.message_remove_alias_failed_2.format(f) + "\n"
    
    return await context.koduck.send_message(receive_message=context.message, content=return_message)

async def list_aliases(context, *args, **kwargs):
    if len(args) < 1:
        return await context.koduck.send_message(receive_message=context.message, content=settings.message_list_aliases_no_param)
    
    #parse params
    aliases = {k.lower():v[0] for k,v in yadon.ReadTable(settings.aliases_table).items()}
    try:
        original = aliases[args[0].lower()]
    except KeyError:
        original = args[0]
    
    #action
    results = []
    for k,v in yadon.ReadTable(settings.aliases_table).items():
        if original.lower() == v[0].lower():
            results.append(k)
    if len(results) == 0:
        return await context.koduck.send_message(receive_message=context.message, content=settings.message_list_aliases_no_result)
    else:
        return await context.koduck.send_message(receive_message=context.message, content=settings.message_list_aliases_result.format(original, ", ".join(results)))

async def last_stage_pokemon(context: KoduckContext) -> discord.Message | None:
    query_ = await latest_stage_query(context)
    if not query_:
        return await context.koduck.send_message(
            receive_message=context.message,
            content=settings.message_no_previous_stage,
        )

    if not (query_.args and "pokemon" in query_.kwargs):
        return await context.koduck.send_message(
            receive_message=context.message,
            content=settings.message_last_query_error
        )

    last_stage_pokemon = query_.kwargs['pokemon']
    return await pokemon(context, last_stage_pokemon)

async def pokemon(context, *args, **kwargs):
    if not args:
        return await last_stage_pokemon(context)
    
    #parse params
    query_pokemon = await pokemon_lookup(context, query=args[0])
    if query_pokemon is None:
        return "Unrecognized Pokemon"
    
    #retrieve data
    values = yadon.ReadRowFromTable(settings.pokemon_table, query_pokemon, named_columns=True)
    if values is None:
        return await context.koduck.send_message(receive_message=context.message, content=settings.message_pokemon_no_result.format(query_pokemon))
    
    return await context.koduck.send_message(receive_message=context.message, embed=embed_formatters.format_pokemon_embed(query_pokemon, values))

async def skill(context, *args, **kwargs):
    if len(args) < 1:
        return await context.koduck.send_message(receive_message=context.message, content=settings.message_skill_no_param)
    
    #parse params
    query_skill = await pokemon_lookup(context, query=args[0], skill_lookup=True)
    if query_skill is None:
        return "Unrecognized Skill"
    
    #retrieve data
    values = yadon.ReadRowFromTable(settings.skills_table, query_skill, named_columns=True)
    if values is None:
        return await context.koduck.send_message(receive_message=context.message, content=settings.message_skill_no_result.format(query_skill))
    
    return await context.koduck.send_message(receive_message=context.message, embed=embed_formatters.format_skill_embed(query_skill, values))

async def ap(context, *args, **kwargs):
    if len(args) < 1:
        return await context.koduck.send_message(receive_message=context.message, content=settings.message_ap_no_param)
    
    query_bp = args[0]
    if query_bp not in ["30", "40", "50", "60", "70", "80", "90"]:
        return await context.koduck.send_message(receive_message=context.message, content=settings.message_ap_invalid_param)
    ap_list = yadon.ReadRowFromTable(settings.ap_table, query_bp)
    
    if len(args) >= 2:
        try:
            query_level = int(args[1])
        except ValueError:
            return await context.koduck.send_message(receive_message=context.message, content=settings.message_ap_invalid_param_2)
        if query_level not in range(1, 31):
            return await context.koduck.send_message(receive_message=context.message, content=settings.message_ap_invalid_param_2)
        return await context.koduck.send_message(receive_message=context.message, content=ap_list[query_level-1])
    else:
        desc = "```"
        for i in range(len(ap_list)):
            if i % 10 == 0:
                desc += "\n"
            if int(ap_list[i]) >= 100:
                desc += "{} ".format(ap_list[i])
            else:
                desc += " {} ".format(ap_list[i])
        desc += "\n```"
        return await context.koduck.send_message(receive_message=context.message, content=desc)

async def exp(context, *args, **kwargs):
    #allow space delimited parameters
    if len(args) == 1:
        args = args[0].split(" ")
    
    if len(args) < 1:
        return await context.koduck.send_message(receive_message=context.message, content=settings.message_exp_no_param)
    
    #parse params
    query = args[0]
    try:
        query_bp = int(query)
        if query_bp < 30 or query_bp > 90 or query_bp % 10 != 0:
            return await context.koduck.send_message(receive_message=context.message, content=settings.message_exp_invalid_param)
    except ValueError:
        query_pokemon = await pokemon_lookup(context, query=query)
        if query_pokemon is None:
            return "Unrecognized Pokemon"
        pokemon_details = yadon.ReadRowFromTable(settings.pokemon_table, query_pokemon, named_columns=True)
        query_bp = int(pokemon_details["BP"])
    
    if len(args) == 1:
        exp_table = yadon.ReadRowFromTable(settings.exp_table, str(query_bp))[1:]
        desc = settings.message_exp_result_3.format(query_bp)
        desc += "\n```"
        for i in range(len(exp_table)):
            if i % 10 == 0:
                desc += "\n"
            desc += exp_table[i].rjust(7)
        desc += "\n```"
        desc += settings.message_exp_result_4.format(query_bp)
        desc += "\n```"
        for i in range(len(exp_table)):
            if i % 10 == 0:
                desc += "\n"
            if i != 0:
                exp_to_next = int(exp_table[i]) - int(exp_table[i-1])
            else:
                exp_to_next = int(exp_table[i])
            desc += str(exp_to_next).rjust(7)
        desc += "\n```"
        return await context.koduck.send_message(receive_message=context.message, content=desc)
    
    if len(args) == 2:
        query_level_1 = 1
        try:
            query_level_2 = int(args[1])
        except ValueError:
            return await context.koduck.send_message(receive_message=context.message, content=settings.message_exp_invalid_param_2)
    else:
        try:
            query_level_1 = int(args[1])
            query_level_2 = int(args[2])
        except ValueError:
            return await context.koduck.send_message(context.message, content=settings.message_exp_invalid_param_2)
    if query_level_1 not in range(1, 31) or query_level_2 not in range(1, 31):
        return await context.koduck.send_message(receive_message=context.message, content=settings.message_exp_invalid_param_2)
    
    #retrieve data
    start_exp = int(yadon.ReadRowFromTable(settings.exp_table, str(query_bp))[query_level_1])
    end_exp = int(yadon.ReadRowFromTable(settings.exp_table, str(query_bp))[query_level_2])
    start_ap = int(yadon.ReadRowFromTable(settings.ap_table, str(query_bp))[query_level_1 - 1])
    end_ap = int(yadon.ReadRowFromTable(settings.ap_table, str(query_bp))[query_level_2 - 1])
    
    if query.isdigit():
        return await context.koduck.send_message(receive_message=context.message, content=settings.message_exp_result.format(query_bp, end_exp - start_exp, query_level_1, start_ap, query_level_2, end_ap))
    else:
        return await context.koduck.send_message(receive_message=context.message, content=settings.message_exp_result_2.format(query_pokemon, query_bp, end_exp - start_exp, query_level_1, start_ap, query_level_2, end_ap))

async def type(context, *args, **kwargs):
    if len(args) < 1:
        return await context.koduck.send_message(receive_message=context.message, content=settings.message_type_no_param)
    query_type = args[0].lower().capitalize()
    values = yadon.ReadRowFromTable(settings.types_table, query_type)
    if values is None:
        return await context.koduck.send_message(receive_message=context.message, content=settings.message_type_invalid_param)
    else:
        return await context.koduck.send_message(receive_message=context.message, embed=embed_formatters.format_type_embed([query_type] + values))

async def latest_stage_query(context: KoduckContext) -> UserQuery | None:
    user_id = context.message.author.id
    query_history = context.koduck.query_history[user_id]

    try:
        query_ = next(q for q in reversed(query_history) if q.type == QueryType.STAGE)
    except StopIteration:
        return

    return query_

async def next_stage(
    context: KoduckContext, *args: str, **kwargs: Any
) -> discord.Message | None:
    query_ = await latest_stage_query(context)

    if not query_:
        return await context.koduck.send_message(
            receive_message=context.message,
            content=settings.message_no_previous_stage,
        )
    if not query_.args:
        return await context.koduck.send_message(
            receive_message=context.message,
            content=settings.message_last_query_error,
        )

    kwargs = query_.kwargs | kwargs

    last_stage_id = query_.args[0]
    if last_stage_id.startswith("s") and last_stage_id[1:].isdigit():
        return await context.koduck.send_message(
            receive_message=context.message,
            content=settings.message_last_query_invalid_stage,
        )
    if last_stage_id.startswith("ex") and last_stage_id[2:].isdigit():
        return await stage(context, f"ex{int(last_stage_id[2:]) + 1}", **kwargs)
    if last_stage_id.isdigit():
        next_id = int(last_stage_id) + 1
        if next_id == 701:
            next_id = 1
        return await stage(context, str(next_id), **kwargs)

    return await context.koduck.send_message(
            receive_message=context.message,
            content=settings.message_last_query_error,
        )

async def next_stage_shorthand(context: KoduckContext, *args: str, **kwargs: Any) -> discord.Message|None:
    kwargs["shorthand"] = True
    return await next_stage(context, *args, **kwargs)

async def stage(context, *args, **kwargs):
    #change current query type to ANY in case stage does not return a stage message
    user_query_history = context.koduck.query_history[context.message.author.id]
    user_query_history[-1] = UserQuery(QueryType.ANY, args=args, kwargs=kwargs)

    if len(args) < 1:
        return await context.koduck.send_message(receive_message=context.message, content=settings.message_stage_no_param)

    #allow space delimited parameters
    if len(args) == 1:
        temp = args[0].split(" ")
        if len(temp) > 1 and temp[-1].isdigit():
            args = ["".join(temp[:-1]), temp[-1]]
    
    result_number = 0
    try:
        shorthand = kwargs["shorthand"]
    except KeyError:
        shorthand = False
    try:
        starting_board = kwargs["startingboard"]
    except KeyError:
        starting_board = False
    
    #parse params
    query_pokemon = args[0]
    if query_pokemon.isdigit():
        stage_type = "main"
        stage_index = int(query_pokemon)
    elif query_pokemon.lower().startswith("ex") and query_pokemon[2:].isdigit():
        stage_type = "expert"
        stage_index = int(query_pokemon[2:])
    elif query_pokemon.lower().startswith("s") and query_pokemon[1:].isdigit():
        stage_type = "event"
        stage_index = int(query_pokemon[1:])
    else:
        stage_type = "all"
    if len(args) >= 2:
        try:
            result_number = int(args[1])
            if result_number <= 0:
                return await context.koduck.send_message(receive_message=context.message, content=settings.message_stage_invalid_param)
        except ValueError:
            return await context.koduck.send_message(receive_message=context.message, content=settings.message_stage_invalid_param)
    
    results = []
    #retrieve data
    if stage_type == "main":
        values = yadon.ReadRowFromTable(settings.main_stages_table, str(stage_index))
        if values is None:
            return await context.koduck.send_message(receive_message=context.message, content=settings.message_stage_main_invalid_param.format(settings.main_stages_min_index, settings.main_stages_max_index))
        results.append([str(stage_index)] + values)
    elif stage_type == "expert":
        values = yadon.ReadRowFromTable(settings.expert_stages_table, str(stage_index))
        if values is None:
            return await context.koduck.send_message(receive_message=context.message, content=settings.message_stage_expert_invalid_param.format(settings.expert_stages_min_index + 1, settings.expert_stages_max_index + 1))
        results.append(["ex{}".format(stage_index)] + values)
    elif stage_type == "event":
        values = yadon.ReadRowFromTable(settings.event_stages_table, str(stage_index))
        if values is None:
            return await context.koduck.send_message(receive_message=context.message, content=settings.message_stage_event_invalid_param.format(settings.event_stages_min_index, settings.event_stages_max_index))
        results.append(["s{}".format(stage_index)] + values)
    elif stage_type == "all":
        query_pokemon = await pokemon_lookup(context, query=query_pokemon)
        if query_pokemon is None:
            return "Unrecognized Pokemon"
        
        #redirect to EB if queried pokemon is in EB table
        eb_details_2 = yadon.ReadRowFromTable(settings.eb_details_table, query_pokemon)
        if eb_details_2 is not None:
            return await eb_details(context, *[query_pokemon], **kwargs)
        
        main_stages = [(v[0],[str(k)]+v) for k,v in yadon.ReadTable(settings.main_stages_table).items()]
        expert_stages = [(v[0],["ex{}".format(k)]+v) for k,v in yadon.ReadTable(settings.expert_stages_table).items()]
        event_stages = [(v[0],["s{}".format(k)]+v) for k,v in yadon.ReadTable(settings.event_stages_table).items()]
        all_stages = main_stages + expert_stages + event_stages
        results = []
        for pokemon, values in all_stages:
            if pokemon.lower() == query_pokemon.lower():
                results.append(values)
    if len(results) == 0:
        no_result_message = await context.koduck.send_message(receive_message=context.message, content=settings.message_stage_no_result.format(query_pokemon))
    
    #if a result number is given
    elif result_number != 0:
        user_query_history[-1] = UserQuery(QueryType.STAGE, args=(results[result_number - 1][0],), kwargs=kwargs | {"pokemon": results[result_number - 1][1]})
        try:
            if starting_board:
                return await context.koduck.send_message(receive_message=context.message, embed=embed_formatters.format_starting_board_embed(results[result_number-1]))
            else:
                return await context.koduck.send_message(receive_message=context.message, embed=embed_formatters.format_stage_embed(results[result_number-1], shorthand=shorthand))
        except IndexError:
            return await context.koduck.send_message(receive_message=context.message, content=settings.message_stage_result_error.format(len(results)))
    
    elif len(results) == 1:
        user_query_history[-1] = UserQuery(QueryType.STAGE, args=(results[0][0],), kwargs=kwargs | {"pokemon": results[0][1]})
        if starting_board:
            return await context.koduck.send_message(receive_message=context.message, embed=embed_formatters.format_starting_board_embed(results[0]))
        else:
            return await context.koduck.send_message(receive_message=context.message, embed=embed_formatters.format_stage_embed(results[0], shorthand=shorthand))
    
    elif len(results) > 1:
        indices = []
        output_string = ""
        for i in range(len(results)):
            values = results[i]
            indices.append(values[0])
            if i < settings.choice_react_limit:
                output_string += "\n{} {}".format(constants.number_emojis[i+1], indices[i])
        
        choice = await choice_react(context, min(len(indices), settings.choice_react_limit), settings.message_stage_multiple_results + output_string)
        if choice is None:
            return
        user_query_history[-1] = UserQuery(QueryType.STAGE, args=(results[choice][0],), kwargs=kwargs | {"pokemon": results[choice][1]})
        if starting_board:
            return await context.koduck.send_message(receive_message=context.message, embed=embed_formatters.format_starting_board_embed(results[choice]))
        else:
            return await context.koduck.send_message(receive_message=context.message, embed=embed_formatters.format_stage_embed(results[choice], shorthand=shorthand))

async def stage_shorthand(context, *args, **kwargs):
    kwargs["shorthand"] = True
    return await stage(context, *args, **kwargs)

async def starting_board(context, *args, **kwargs):
    kwargs["startingboard"] = True
    return await stage(context, *args, **kwargs)

async def disruption_pattern(context, *args, **kwargs):
    if len(args) < 1:
        return await context.koduck.send_message(receive_message=context.message, content=settings.message_dp_no_param)
    
    #parse params
    try:
        query_index = int(args[0])
    except ValueError:
        return await context.koduck.send_message(receive_message=context.message, content=settings.message_dp_invalid_param.format(settings.disruption_patterns_min_index, settings.disruption_patterns_max_index))
    
    if query_index % 6 != 0 or query_index < settings.disruption_patterns_min_index or query_index > settings.disruption_patterns_max_index:
        return await context.koduck.send_message(receive_message=context.message, content=settings.message_dp_invalid_param.format(settings.disruption_patterns_min_index, settings.disruption_patterns_max_index))
    
    embed = discord.Embed()
    embed.set_image(url="https://raw.githubusercontent.com/Chupalika/Kaleo/icons/Disruption Patterns/Pattern Index {}.png".format(query_index).replace(" ", "%20"))
    return await context.koduck.send_message(receive_message=context.message, embed=embed)

async def event(context, *args, **kwargs):
    if len(args) < 1:
        return await context.koduck.send_message(receive_message=context.message, content=settings.message_event_no_param)
    
    #allow space delimited parameters
    if len(args) == 1:
        temp = args[0].split(" ")
        if len(temp) > 1 and temp[-1].isdigit():
            args = ["".join(temp[:-1]), temp[-1]]
    
    result_number = 1
    
    #parse params
    if len(args) >= 2:
        try:
            result_number = int(args[1])
            if result_number <= 0:
                return await context.koduck.send_message(receive_message=context.message, content=settings.message_event_invalid_param)
        except ValueError:
            return await context.koduck.send_message(receive_message=context.message, content=settings.message_event_invalid_param)
    query_pokemon = await pokemon_lookup(context, query=args[0])
    if query_pokemon is None:
        return "Unrecognized Pokemon"
    
    #retrieve data
    results = []
    for k,v in yadon.ReadTable(settings.events_table).items():
        event_pokemon = [x.lower() for x in v[1].split("/")]
        if query_pokemon.lower() in event_pokemon:
            results.append([k]+v)
    
    try:
        values = results[result_number-1]
    except IndexError:
        if len(results) != 0:
            return await context.koduck.send_message(receive_message=context.message, content=settings.message_event_result_error.format(len(results)))
        else:
            return await context.koduck.send_message(receive_message=context.message, content=settings.message_event_no_result.format(query_pokemon))
    
    if len(results) > 1:
        return await paginate_embeds(context, [embed_formatters.format_event_embed(values) for values in results], result_number)
    else:
        return await context.koduck.send_message(receive_message=context.message, embed=embed_formatters.format_event_embed(values))

async def paginate_embeds(context, pages, initial_page=1):
    current_page = initial_page
    the_message = await context.koduck.send_message(receive_message=context.message, content="Showing result {} of {}".format(current_page, len(pages)), embed=pages[current_page-1])
    
    await the_message.add_reaction("⬅️")
    await the_message.add_reaction("➡️")
    
    while True:
        #wait for reaction (with timeout)
        def check(reaction, user):
            return reaction.message.id == the_message.id and user == context.message.author and str(reaction.emoji) in ["⬅️", "➡️"]
        try:
            reaction, _ = await context.koduck.client.wait_for('reaction_add', timeout=settings.dym_timeout, check=check)
        except asyncio.TimeoutError:
            reaction = None
        
        #timeout
        if reaction == None:
            break
        
        #adjust page
        if reaction.emoji == "⬅️":
            current_page -= 1
        elif reaction.emoji == "➡️":
            current_page += 1
        
        #wrap
        if current_page < 1:
            current_page = len(pages)
        elif current_page > len(pages):
            current_page = 1
        
        await the_message.edit(content="Showing result {} of {}".format(current_page, len(pages)), embed=pages[current_page-1])
    
    #remove reactions
    try:
        await the_message.remove_reaction("⬅️", context.koduck.client.user)
        await the_message.remove_reaction("➡️", context.koduck.client.user)
    except discord.errors.NotFound:
        pass
    
    return the_message

def validate_query(subqueries):
    #allow space delimited parameters
    if len(subqueries) == 1 and len(subqueries[0].split("=")) > 2:
        subqueries = subqueries[0].split(" ")
        new_subqueries = []
        for subquery in subqueries:
            operation = ""
            for op in [">=", "<=", "=>", "=<", ">", "<", "!=", "="]:
                if len(subquery.split(op)) == 2:
                    operation = op
                    break
            if operation == "" and len(new_subqueries) > 0:
                new_subqueries[-1] = new_subqueries[-1] + " " + subquery
            else:
                new_subqueries.append(subquery)
        subqueries = new_subqueries
    
    validated_queries = []
    for subquery in subqueries:
        subquery = subquery.strip()
        #accept five (seven) different operations
        operation = ""
        for op in [">=", "<=", "=>", "=<", ">", "<", "!=", "="]:
            if len(subquery.split(op)) == 2:
                operation = op
                break
        if operation == "":
            continue
        
        #split
        left = subquery.split(operation)[0].strip().lower()
        if left not in ["dex", "type", "bp", "rml", "rmls", "maxap", "skill", "sk", "sortby", "se", "evospeed", "megaspeed", "name"]:
            continue
        if left in ["type", "skill", "sk", "sortby", "se", "name"] and operation not in ["=", "!="]:
            continue
        
        right = subquery.split(operation)[1].strip()
        if right == "":
            continue
        
        #skills maybe used an alias
        if left in ["skill", "sk"]:
            right = utils.alias(right.lower())
        #make sure these are integers...
        elif left in ["dex", "bp", "rml", "rmls", "maxap", "evospeed", "megaspeed"]:
            try:
                right = int(right)
            except ValueError:
                continue
        #make sure type and se are valid types
        elif left in ["type", "se"]:
            right = right.lower().capitalize()
            type_details = yadon.ReadRowFromTable(settings.types_table, right)
            if type_details is None:
                continue
        
        validated_queries.append((left, operation, right))
    
    return validated_queries

def pokemon_filter_results_to_string(buckets, use_emojis=False):
    farmable_pokemon = utils.get_farmable_pokemon()
    output_string = ""
    for bucket_key in buckets.keys():
        output_string += "\n**{}**: ".format(bucket_key)
        for item in buckets[bucket_key]:
            farmable = item.replace("**", "") in farmable_pokemon
            if use_emojis:
                try:
                    #surround ss pokemon with parentheses (instead of boldifying it, because, y'know... can't boldify emojis)
                    if item.find("**") != -1:
                        output_string += "([{}])".format(item.replace("**", ""))
                    else:
                        output_string += "[{}]".format(item)
                    if farmable:
                        output_string += "\*"
                except KeyError:
                    output_string += "{}{} ".format("**" + item if item.find("**") != -1 else item, "\*" if farmable else "")
            else:
                output_string += "{}{}, ".format("**" + item if item.find("**") != -1 else item, "\*" if farmable else "")
        if not use_emojis:
            output_string = output_string[:-2]
        else:
            output_string = utils.emojify(output_string)
    return output_string

async def query(context, *args, **kwargs):
    try:
        use_emojis = kwargs["useemojis"]
    except KeyError:
        use_emojis = False
    
    queries = validate_query(context["params"])
    
    farmable = 0
    if "farmable" in args:
        farmable = 1
    if "!farmable" in args:
        farmable = 2
    if "?farmable" in args:
        farmable = 3
    if "farmable" in kwargs:
        if kwargs["farmable"] == "yes":
            farmable = 1
        elif kwargs["farmable"] == "no":
            farmable = 2
        elif kwargs["farmable"] == "both":
            farmable = 3
    
    ss_filter = 0
    if "ss" in args:
        ss_filter = 1
    if "!ss" in args:
        ss_filter = 2
    if "ss" in kwargs:
        if kwargs["ss"] == "yes":
            ss_filter = 1
        elif kwargs["ss"] == "no":
            ss_filter = 2
    
    #force mega if evospeed is used
    if "evospeed" in [x[0] for x in queries] or "evospeed" in [x[2] for x in queries if x[0] == "sortby"] or "megaspeed" in [x[0] for x in queries] or "megaspeed" in [x[2] for x in queries if x[0] == "sortby"]:
        kwargs["mega"] = True
    
    #generate a string to show which filters were recognized
    query_string = ""
    sortby = ""
    if "mega" in args or "mega" in kwargs:
        query_string += "mega and "
    if "hasmega" in args or "hasmega" in kwargs:
        query_string += "hasmega and "
    if farmable == 1:
        query_string += "farmable and "
    elif farmable == 2:
        query_string += "not farmable and "
    if ss_filter == 1:
        query_string += "only-SS and "
    elif ss_filter == 2:
        query_string += "no-SS and "
    for subquery in queries:
        left, operation, right = subquery
        if right != "":
            query_string += "{}{}{} and ".format(left, operation, right)
            if left == "sortby":
                sortby = right
    if query_string != "":
        query_string = query_string[:-5]
    else:
        return await context.koduck.send_message(receive_message=context.message, content=settings.message_query_invalid_param)
    
    hits, hits_bp, hits_max_ap, hits_type, hits_evo_speed = pokemon_filter(queries, "mega" in args or "mega" in kwargs, "fake" in args or "fake" in kwargs, farmable, ss_filter, "hasmega" in args or "hasmega" in kwargs)
    
    #sort results and create a string to send
    header = settings.message_query_result.format(len(hits), query_string, "{}")
    
    #format output depending on which property to sort by
    if sortby == "bp":
        buckets = {k:sorted(hits_bp[k]) for k in sorted(hits_bp.keys())}
        sortby_string = "BP"
    elif sortby == "type":
        buckets = {k:sorted(hits_type[k]) for k in sorted(hits_type.keys())}
        sortby_string = "Type"
    elif sortby in ["evospeed", "megaspeed"] and ("mega" in args or "mega" in kwargs):
        buckets = {k:sorted(hits_evo_speed[k]) for k in sorted(hits_evo_speed.keys())}
        sortby_string = "Mega Evolution Speed"
    else:
        buckets = {k:sorted(hits_max_ap[k]) for k in sorted(hits_max_ap.keys())}
        sortby_string = "Max AP"
    header = header.format(sortby_string)
    return await context.koduck.send_message(receive_message=context.message, embed=embed_formatters.format_query_results_embed(header, buckets, use_emojis))

async def query_with_emojis(context, *args, **kwargs):
    kwargs["useemojis"] = True
    return await query(context, *args, **kwargs)

async def skill_with_pokemon(context, *args, **kwargs):
    try:
        use_emojis = kwargs["useemojis"]
    except KeyError:
        use_emojis = False
    
    if len(args) < 1:
        return await context.koduck.send_message(receive_message=context.message, content=settings.message_skill_no_param)
    
    query_skill = args[0]
    
    #lookup and validate skill
    query_skill = await pokemon_lookup(context, query=query_skill, skill_lookup=True)
    if query_skill is None:
        return "Unrecognized Skill"
    
    #retrieve skill data
    values = yadon.ReadRowFromTable(settings.skills_table, query_skill, named_columns=True)
    if values is None:
        return await context.koduck.send_message(receive_message=context.message, content=settings.message_skill_no_result.format(query_skill))
    
    copy_of_params = context["params"].copy()
    copy_of_params.remove(args[0])
    queries = validate_query(copy_of_params)
    
    farmable = 0
    if "farmable" in args:
        farmable = 1
    if "!farmable" in args:
        farmable = 2
    if "?farmable" in args:
        farmable = 3
    if "farmable" in kwargs:
        if kwargs["farmable"] == "yes":
            farmable = 1
        elif kwargs["farmable"] == "no":
            farmable = 2
        elif kwargs["farmable"] == "both":
            farmable = 3
    
    ss_filter = 0
    if "ss" in args:
        ss_filter = 1
    if "!ss" in args:
        ss_filter = 2
    if "ss" in kwargs:
        if kwargs["ss"] == "yes":
            ss_filter = 1
        elif kwargs["ss"] == "no":
            ss_filter = 2
    
    #force mega if evospeed is used
    if "evospeed" in [x[0] for x in queries] or "evospeed" in [x[2] for x in queries if x[0] == "sortby"] or "megaspeed" in [x[0] for x in queries] or "megaspeed" in [x[2] for x in queries if x[0] == "sortby"]:
        kwargs["mega"] = True
    
    #generate a string to show which filters were recognized
    query_string = ""
    sortby = ""
    if "mega" in args or "mega" in kwargs:
        query_string += "mega and "
    if "hasmega" in args or "hasmega" in kwargs:
        query_string += "hasmega and "
    if farmable == 1:
        query_string += "farmable and "
    elif farmable == 2:
        query_string += "not farmable and "
    if ss_filter == 1:
        query_string += "only-SS and "
    elif ss_filter == 2:
        query_string += "no-SS and "
    for subquery in queries:
        left, operation, right = subquery
        if right != "":
            query_string += "{}{}{} and ".format(left, operation, right)
            if left == "sortby":
                sortby = right
    if query_string != "":
        query_string = query_string[:-5]
    
    #query for pokemon with this skill
    queries.append(("skill", "=", query_skill))
    hits, hits_bp, hits_max_ap, hits_type, hits_evo_speed = pokemon_filter(queries, "mega" in args or "mega" in kwargs, "fake" in args or "fake" in kwargs, farmable, ss_filter, "hasmega" in args or "hasmega" in kwargs)
    
    #format output
    if len(hits) == 0:
        field_value = "None"
        sortby_string = ""
    else:
        #format output depending on which property to sort by (default maxap)
        if sortby == "bp":
            buckets = {k:sorted(hits_bp[k]) for k in sorted(hits_bp.keys())}
            sortby_string = "BP"
        elif sortby == "type":
            buckets = {k:sorted(hits_type[k]) for k in sorted(hits_type.keys())}
            sortby_string = "Type"
        elif sortby in ["evospeed", "megaspeed"] and ("mega" in args or "mega" in kwargs):
            buckets = {k:sorted(hits_evo_speed[k]) for k in sorted(hits_evo_speed.keys())}
            sortby_string = "Mega Evolution Speed"
        else:
            buckets = {k:sorted(hits_max_ap[k]) for k in sorted(hits_max_ap.keys())}
            sortby_string = "Max AP"
        field_value = pokemon_filter_results_to_string(buckets, use_emojis)
    field_name = "Pokemon with this skill{}{}".format(" ({})".format(query_string) if query_string else "", " sorted by {}".format(sortby_string) if sortby_string else "")
    
    embed = embed_formatters.format_skill_embed(query_skill, values)
    embed.add_field(name=field_name, value=field_value)
    return await context.koduck.send_message(receive_message=context.message, embed=embed)

async def skill_with_pokemon_with_emojis(context, *args, **kwargs):
    kwargs["useemojis"] = True
    return await skill_with_pokemon(context, *args, **kwargs)

#Helper function for query command
#farmable/ss_filter: 0 = ignore, 1 = include, 2 = exclude
def pokemon_filter(queries, mega=False, include_fake=False, farmable=0, ss_filter=0, has_mega=False):
    hits = []
    hits_bp = {}
    hits_type = {}
    hits_max_ap = {}
    hits_evo_speed = {}
    
    se_types = []
    for subquery in queries:
        left, operation, right = subquery
        if left == "se":
            type_details = yadon.ReadRowFromTable(settings.types_table, right)
            se_types.extend(type_details[2].split(", ") if type_details else [])
    
    if farmable != 0:
        farmable_pokemon = utils.get_farmable_pokemon()
    
    #check each pokemon
    pokedex = yadon.ReadTable(settings.pokemon_table, named_columns=True)
    for name, details in pokedex.items():
        try:
            dex = int(details["Dex"])
        except ValueError:
            dex = 999
        type = details["Type"]
        try:
            bp = int(details["BP"])
        except ValueError:
            bp = 0
        try:
            rmls = int(details["RML"])
        except ValueError:
            rmls = 0
        try:
            max_ap = int(details["MaxAP"])
        except ValueError:
            max_ap = 0
        skill = details["Skill"]
        ss = details["SS"]
        try:
            icons = int(details["Icons"])
        except ValueError:
            icons = 0
        try:
            msu = int(details["MSU"])
        except ValueError:
            msu = 0
        mega_power = details["Mega Power"]
        evo_speed = icons - msu
        
        if not mega and mega_power:
            continue
        if mega and not mega_power:
            continue
        
        if has_mega and name in ["Charizard", "Mewtwo", "Charizard (Shiny)"]:
            pass
        elif has_mega and "Mega {}".format(name) not in pokedex.keys():
            continue
        
        if not include_fake and details["Fake"]:
            continue
        
        if farmable == 1 and name not in farmable_pokemon:
            continue
        
        if farmable == 2 and name in farmable_pokemon:
            continue
        
        temp_ss = [x.lower() for x in ss.split("/")]
        
        result = True
        is_ss = False
        for subquery in queries:
            left, operation, right = subquery
            
            if (left == "dex") and \
                ((operation in [">=", "=>"] and dex < right) or \
                (operation in ["<=", "=<"] and dex > right) or \
                (operation == ">" and dex <= right) or \
                (operation == "<" and dex >= right) or \
                (operation == "=" and dex != right) or \
                (operation == "!=" and dex == right)):
                    result = False
                    break
            if (left == "bp") and \
                ((operation in [">=", "=>"] and bp < right) or \
                (operation in ["<=", "=<"] and bp > right) or \
                (operation == ">" and bp <= right) or \
                (operation == "<" and bp >= right) or \
                (operation == "=" and bp != right) or \
                (operation == "!=" and bp == right)):
                    result = False
                    break
            if (left in ["rml", "rmls"]) and \
                ((operation in [">=", "=>"] and rmls < right) or \
                (operation in ["<=", "=<"] and rmls > right) or \
                (operation == ">" and rmls <= right) or \
                (operation == "<" and rmls >= right) or \
                (operation == "=" and rmls != right) or \
                (operation == "!=" and rmls == right)):
                    result = False
                    break
            if (left == "maxap") and \
                ((operation in [">=", "=>"] and max_ap < right) or \
                (operation in ["<=", "=<"] and max_ap > right) or \
                (operation == ">" and max_ap <= right) or \
                (operation == "<" and max_ap >= right) or \
                (operation == "=" and max_ap != right) or \
                (operation == "!=" and max_ap == right)):
                    result = False
                    break
            if (left == "type") and \
                ((operation == "=" and right.lower() != type.lower()) or \
                (operation == "!=" and right.lower() == type.lower())):
                    result = False
                    break
            if (left == "se") and \
                ((operation == "=" and type not in se_types) or \
                (operation == "!=" and type in se_types)):
                    result = False
                    break
            if (left in ["skill", "sk"]) and \
                ((operation == "=" and right.lower() != skill.lower() and right.lower() not in temp_ss) or \
                (operation == "!=" and (right.lower() == skill.lower() or right.lower() in temp_ss))):
                    result = False
                    break
            if left in ["skill", "sk"] and operation == "=" and right.lower() in temp_ss:
                is_ss = True
                if ss_filter == 2:
                    result = False
            else:
                if ss_filter == 1:
                    result = False
            if (left in ["evospeed", "megaspeed"]) and \
                ((operation in [">=", "=>"] and evo_speed < right) or \
                (operation in ["<=", "=<"] and evo_speed > right) or \
                (operation == ">" and evo_speed <= right) or \
                (operation == "<" and evo_speed >= right) or \
                (operation == "=" and evo_speed != right) or \
                (operation == "!=" and evo_speed == right)):
                    result = False
                    break
            if (left == "name") and \
                ((operation == "=" and right.lower() not in name.lower()) or \
                (operation == "!=" and (right.lower() in name.lower()))):
                    result = False
                    break
        if not result:
            continue
        
        #if skill is used, boldify pokemon with ss
        #it can't start with ** because it needs to be sorted by name
        if is_ss:
            hit_name = "{}**".format(name)
        else:
            hit_name = name
        
        if farmable == 3 and name in farmable_pokemon:
            hit_name += "\*"
        
        try:
            hits_bp[bp].append(hit_name)
        except KeyError:
            hits_bp[bp] = [hit_name]
        
        try:
            hits_max_ap[max_ap].append(hit_name)
        except KeyError:
            hits_max_ap[max_ap] = [hit_name]
        
        try:
            hits_type[type].append(hit_name)
        except KeyError:
            hits_type[type] = [hit_name]
        
        try:
            hits_evo_speed[evo_speed].append(hit_name)
        except KeyError:
            hits_evo_speed[evo_speed] = [hit_name]
        
        hits.append(hit_name)
    
    return (hits, hits_bp, hits_max_ap, hits_type, hits_evo_speed)

async def eb_rewards(context, *args, **kwargs):
    if len(args) < 1:
        query_pokemon = utils.current_eb_pokemon()
    else:
        #parse params
        query_pokemon = await pokemon_lookup(context, query=args[0])
        if query_pokemon is None:
            return "Unrecognized Pokemon"
    
    #retrieve data
    eb_rewards = yadon.ReadRowFromTable(settings.eb_rewards_table, query_pokemon)
    if eb_rewards is None:
        return await context.koduck.send_message(receive_message=context.message, content=settings.message_eb_rewards_no_result.format(query_pokemon))
    
    return await context.koduck.send_message(receive_message=context.message, embed=embed_formatters.format_eb_rewards_embed([query_pokemon] + eb_rewards))

async def eb_details(context, *args, **kwargs):
    if len(args) < 1 or args[0].isdigit():
        eb_pokemon = utils.current_eb_pokemon()
        args = [eb_pokemon] + list(args)
    
    #allow space delimited parameters
    if len(args) == 1:
        temp = args[0].split(" ")
        if len(temp) > 1 and temp[-1].isdigit():
            args = [" ".join(temp[:-1]), temp[-1]]
    
    query_level = 0
    if len(args) >= 2:
        query_level = args[1]
        try:
            if int(query_level) <= 0:
                return await context.koduck.send_message(receive_message=context.message, content=settings.message_eb_invalid_param)
            query_level = int(query_level)
        except ValueError:
            return await context.koduck.send_message(receive_message=context.message, content=settings.message_eb_invalid_param)
    
    #parse params
    query_pokemon = await pokemon_lookup(context, query=args[0])
    if query_pokemon is None:
        return "Unrecognized Pokemon"
    
    #verify that queried pokemon is in EB table
    eb_details_2 = yadon.ReadRowFromTable(settings.eb_details_table, query_pokemon)
    if eb_details_2 is None:
        return await context.koduck.send_message(receive_message=context.message, content=settings.message_eb_no_result.format(query_pokemon))
    
    #optional level param which will return a stage embed instead
    if query_level > 0:
        #should be in increasing order
        for level_set in eb_details_2:
            start_level, end_level, stage_index = level_set.split("/")
            if int(end_level) < 0 or query_level < int(end_level):
                break
        values = yadon.ReadRowFromTable(settings.event_stages_table, stage_index)
        
        #extra string to show level range of this eb stage
        if int(start_level) == int(end_level) - 1:
            level_range = " (Level {})".format(start_level)
        elif int(end_level) < 0:
            level_range = " (Levels {}+ ({}))".format(start_level, query_level)
        else:
            level_range = " (Levels {} to {} ({}))".format(start_level, int(end_level) - 1, query_level)
        delta = query_level - int(start_level)
        
        try:
            shorthand = kwargs["shorthand"]
        except KeyError:
            shorthand = False
        try:
            starting_board = kwargs["startingboard"]
        except KeyError:
            starting_board = False
        
        stage_info = ["s{}".format(stage_index)] + values

        user_id = context.message.author.id
        query_history = context.koduck.query_history[user_id]
        query_history[-1] = UserQuery(QueryType.STAGE, (f"s{stage_index}",), kwargs | {"pokemon": query_pokemon})

        eb_reward = ""
        eb_rewards = yadon.ReadRowFromTable(settings.eb_rewards_table, query_pokemon)
        for entry in eb_rewards:
            level, reward_item, reward_amount = entry.split("/")
            if int(level) == query_level:
                eb_reward = "[{}] x{}".format(reward_item, reward_amount)
                break
        
        if starting_board:
            return await context.koduck.send_message(receive_message=context.message, embed=embed_formatters.format_starting_board_embed(stage_info))
        else:
            return await context.koduck.send_message(receive_message=context.message, embed=embed_formatters.format_stage_embed(stage_info, eb_data=(level_range, delta, eb_reward, query_level), shorthand=shorthand))
    
    else:
        return await context.koduck.send_message(receive_message=context.message, embed=embed_formatters.format_eb_details_embed([query_pokemon] + eb_details_2))

async def eb_details_shorthand(context, *args, **kwargs):
    kwargs["shorthand"] = True
    return await eb_details(context, *args, **kwargs)

async def week(context, *args, **kwargs):
    if len(args) < 1:
        query_week = utils.get_current_week()
    else:
        if args[0].isdigit():
            try:
                query_week = int(args[0])
            except ValueError:
                return await context.koduck.send_message(receive_message=context.message, content=settings.message_week_invalid_param.format(settings.num_weeks, settings.num_weeks))
        else:
            query_pokemon = await pokemon_lookup(context, query=args[0])
            if query_pokemon is None:
                return "Unrecognized Pokemon"
            
            #retrieve data
            results = []
            for k,v in yadon.ReadTable(settings.events_table).items():
                event_pokemon = [x.lower() for x in v[1].split("/")]
                if query_pokemon.lower() in event_pokemon:
                    week = v[4]
                    results.append(week)
            if len(results) < 1:
                return await context.koduck.send_message(receive_message=context.message, content=settings.message_event_no_result.format(query_pokemon))
            sorted_results = [int(x)+1 for x in results if int(x)+1 >= utils.get_current_week()] + [int(x)+1 for x in results if int(x)+1 < utils.get_current_week()]
            query_week = sorted_results[0]
        if query_week < 1 or query_week > settings.num_weeks:
            return await context.koduck.send_message(receive_message=context.message, content=settings.message_week_invalid_param.format(settings.num_weeks, settings.num_weeks))
    
    return await context.koduck.send_message(receive_message=context.message, embed=embed_formatters.format_week_embed(query_week))

async def next_week(context, *args, **kwargs):
    args = [str(utils.get_current_week() % 24 + 1)]
    return await week(context, *args, **kwargs)

async def sm_rewards(context, *args, **kwargs):
    table = yadon.ReadTable(settings.sm_rewards_table)
    level = ""
    first_clear = ""
    repeat_clear = ""
    for k,v in table.items():
        level += "{}\n".format(k)
        first_clear += utils.emojify("[{}] x{}\n".format(v[0], v[1]))
        repeat_clear += utils.emojify("[{}] x{}\n".format(v[2], v[3]))
    
    embed = discord.Embed(title="Survival Mode Rewards", color=0xff0000)
    embed.add_field(name="Level", value=level, inline=True)
    embed.add_field(name="First Clear", value=first_clear, inline=True)
    embed.add_field(name="Repeat Clear", value=repeat_clear, inline=True)
    return await context.koduck.send_message(receive_message=context.message, embed=embed)

async def drain_list(context, *args, **kwargs):
    #allow space delimited parameters
    if len(args) == 1:
        args = args[0].split(" ")
    
    #first arg script name, second arg hp, third arg moves
    if len(args) != 2:
        return await context.koduck.send_message(receive_message=context.message, content=settings.message_drain_list_no_param)
 
    try:
        hp = int(args[0])
        moves = int(args[1])
    except ValueError:
        return await context.koduck.send_message(receive_message=context.message, content=settings.message_drain_list_invalid_param)
    
    if hp <= 0 or moves <= 0:
        return await context.koduck.send_message(receive_message=context.message, content=settings.message_drain_list_invalid_param)
    
    if moves > 55:
        return await context.koduck.send_message(receive_message=context.message, content=settings.message_drain_list_invalid_param_2)
 
    output = "```\nhp:    {}\nmoves: {}\n\n".format(str(hp), str(moves))
 
    for i in range(moves):
        drain_amount = int(floor(float(hp) * 0.1))
        output += '{:>2}: {:>5} ({:>6} => {:>6})\n'.format(moves - i, drain_amount, hp, hp - drain_amount)
        hp -= drain_amount
    
    output += "```"
    
    return await context.koduck.send_message(receive_message=context.message, content=output)

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
            return choices[result][1]
    
    else:
        return query

async def submit_comp_score(context, *args, **kwargs):
    if len(args) < 3:
        return await context.koduck.send_message(receive_message=context.message, content=settings.message_submit_comp_score_no_param)
    
    #parse and check competition pokemon
    query_pokemon = await pokemon_lookup(context, query=args[0])
    if query_pokemon is None:
        return "Unrecognized Pokemon"
    comp_pokemon = set()
    for values in yadon.ReadTable(settings.events_table).values():
        if values[0] == "Competitive":
            comp_pokemon.add(values[1])
    if query_pokemon not in comp_pokemon:
        return await context.koduck.send_message(receive_message=context.message, content=settings.message_submit_comp_score_no_result.format(query_pokemon))
    
    #verify score is an integer > 0
    if not args[1].isdigit():
        return await context.koduck.send_message(receive_message=context.message, content=settings.message_submit_comp_score_invalid_param)
    score = int(args[1])
    
    #very screenshot link
    link = args[2]
    if not link.startswith("https://cdn.discordapp.com/attachments/"):
        return await context.koduck.send_message(receive_message=context.message, content=settings.message_submit_comp_score_invalid_param_2)
    
    yadon.WriteRowToTable(settings.comp_scores_table, settings.current_comp_score_id, {"User ID": context.message.author.id, "Competition Pokemon": query_pokemon, "Score": score, "URL": link, "Verified": 0}, named_columns=True)
    context.koduck.update_setting("current_comp_score_id", settings.current_comp_score_id + 1, settings.max_user_level)
    return await context.koduck.send_message(receive_message=context.message, content=settings.message_submit_comp_score_success)

async def comp_scores(context, *args, **kwargs):
    user_id = context.message.author.id
    user_tag = "{}#{}".format(context.message.author.name, context.message.author.discriminator)
    comp_scores = yadon.ReadTable(settings.comp_scores_table, named_columns=True)
    user_comp_scores = [x for x in comp_scores.values() if int(x["User ID"]) == user_id]
    if len(user_comp_scores) == 0:
        return await context.koduck.send_message(receive_message=context.message, content=settings.message_comp_scores_no_result.format(user_tag))
    
    user_comp_scores = sorted(user_comp_scores, key=lambda comp_score: comp_score["Score"])
    comp_scores_string = "``Competition Pokemon\tScore\tVerified\tURL``"
    for comp_score in user_comp_scores:
        comp_scores_string += "\n``{}\t{}\t{}\t``[link]({})".format(comp_score["Competition Pokemon"], comp_score["Score"], "Yes" if int(comp_score["Verified"]) else "No", comp_score["URL"])
    embed = discord.Embed(title=settings.message_comp_scores.format(user_tag), description=comp_scores_string)
    
    return await context.koduck.send_message(receive_message=context.message, embed=embed)

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

async def remind_me(context, *args, **kwargs):
    user_reminders = yadon.ReadRowFromTable(settings.reminders_table, context.message.author.id)
    if not user_reminders:
        user_reminders = ["", ""]
    if len(args) > 0 and args[0].isdigit():
        try:
            query_week = int(args[0])
            if query_week < 1 or query_week > settings.num_weeks:
                raise ValueError()
        except ValueError:
            return await context.koduck.send_message(receive_message=context.message, content=settings.message_week_invalid_param.format(settings.num_weeks, settings.num_weeks))
        if str(query_week) in user_reminders[0].split("/"):
            return await context.koduck.send_message(receive_message=context.message, content=settings.message_remind_me_week_exists)
        reminder_weeks = user_reminders[0].split("/") if user_reminders[0] else []
        reminder_weeks.append(str(query_week))
        user_reminders[0] = "/".join(reminder_weeks)
        yadon.WriteRowToTable(settings.reminders_table, context.message.author.id, user_reminders)
        return await context.koduck.send_message(receive_message=context.message, content=settings.message_remind_me_week_success.format(query_week))
    elif len(args) > 0:
        query_pokemon = await pokemon_lookup(context, query=args[0])
        if query_pokemon is None:
            return "Unrecognized Pokemon"
        if query_pokemon in user_reminders[1].split("/"):
            return await context.koduck.send_message(receive_message=context.message, content=settings.message_remind_me_pokemon_exists)
        reminder_pokemon = user_reminders[1].split("/") if user_reminders[1] else []
        reminder_pokemon.append(query_pokemon)
        user_reminders[1] = "/".join(reminder_pokemon)
        yadon.WriteRowToTable(settings.reminders_table, context.message.author.id, user_reminders)
        return await context.koduck.send_message(receive_message=context.message, content=settings.message_remind_me_pokemon_success.format(query_pokemon))
    else:
        return await context.koduck.send_message(receive_message=context.message, content=settings.message_remind_me_status.format(user_reminders[0], user_reminders[1]))

async def unremind_me(context, *args, **kwargs):
    if len(args) < 1:
        return await context.koduck.send_message(receive_message=context.message, content=settings.message_unremind_me_no_param)
    
    user_reminders = yadon.ReadRowFromTable(settings.reminders_table, context.message.author.id)
    if not user_reminders:
        user_reminders = ["", ""]
    
    if args[0].isdigit():
        try:
            query_week = int(args[0])
            if query_week < 1 or query_week > settings.num_weeks:
                raise ValueError()
        except ValueError:
            return await context.koduck.send_message(receive_message=context.message, content=settings.message_week_invalid_param.format(settings.num_weeks, settings.num_weeks))
        if str(query_week) not in user_reminders[0].split("/"):
            return await context.koduck.send_message(receive_message=context.message, content=settings.message_unremind_me_week_non_exists)
        reminder_weeks = user_reminders[0].split("/") if user_reminders[0] else []
        reminder_weeks.remove(str(query_week))
        user_reminders[0] = "/".join(reminder_weeks)
        yadon.WriteRowToTable(settings.reminders_table, context.message.author.id, user_reminders)
        return await context.koduck.send_message(receive_message=context.message, content=settings.message_unremind_me_week_success.format(query_week))
    else:
        query_pokemon = await pokemon_lookup(context, query=args[0])
        if query_pokemon is None:
            return "Unrecognized Pokemon"
        if query_pokemon not in user_reminders[1].split("/"):
            return await context.koduck.send_message(receive_message=context.message, content=settings.message_unremind_me_pokemon_non_exists)
        reminder_pokemon = user_reminders[1].split("/") if user_reminders[1] else []
        reminder_pokemon.remove(query_pokemon)
        user_reminders[1] = "/".join(reminder_pokemon)
        yadon.WriteRowToTable(settings.reminders_table, context.message.author.id, user_reminders)
        return await context.koduck.send_message(receive_message=context.message, content=settings.message_unremind_me_pokemon_success.format(query_pokemon))

current_day = -1
current_week = -1
async def background_task(koduck_instance):
    global current_day
    global current_week
    current_time = datetime.datetime.now(tz=pytz.timezone('Etc/GMT+6'))
    
    if current_day == -1 or current_week == -1:
        current_day = current_time.day
        current_week = utils.get_current_week()
    
    elif current_time.day != current_day:
        current_day = current_time.day
        current_week2 = utils.get_current_week()
        week_changed = False
        if current_week2 != current_week:
            current_week = current_week2
            week_changed = True
        event_pokemon = utils.get_current_event_pokemon()
        reminders = yadon.ReadTable(settings.reminders_table)
        for userid, v in reminders.items():
            reminder_strings = []
            reminder_weeks = v[0].split("/")
            reminder_pokemon = v[1].split("/")
            if week_changed and str(current_week) in reminder_weeks:
                reminder_strings.append(settings.message_reminder_week.format(current_week))
            for ep in event_pokemon:
                if ep in reminder_pokemon:
                    reminder_strings.append(settings.message_reminder_pokemon.format(ep))
            if reminder_strings:
                the_user = await koduck_instance.client.fetch_user(userid)
                await the_user.send(content=settings.message_reminder_header.format(userid, "\n".join(reminder_strings)))

settings.background_task = background_task