#!/usr/bin/env python3

import os,re,difflib,json
import utils, yadon, settings

scriptdir=os.path.dirname(os.path.realpath(__file__))+os.sep
shuffle_calc_json_filename="{}{}".format(scriptdir,"shuffle_calc_data.json")

def initialize_shuffle_calc_json_data(_filename):
	json_data={}
	if os.path.isfile(_filename):
		with open(_filename) as json_file:
			try:json_data=json.load(json_file)
			except Exception as e:
				print(str(e))
				if test_mode:print_custom(str(e))
	jk=json_data.keys()
	sm_data=json_data["sm_teams"] if "sm_teams" in jk else []
	wm_data=json_data["wm_teams"] if "wm_teams" in jk else []
	sm_stages_data=json_data["sm_stages_results"] if "sm_stages_results" in jk else []
	explain_data=json_data["explainations"] if "explainations" in jk else []
	sm_stage_aliases_by_stage=[k["aliases"] for k in sm_stages_data]
	sm_stage_aliases=[m for k in sm_stages_data for m in k["aliases"]]
	return (sm_stages_data,sm_stage_aliases_by_stage,sm_stage_aliases,sm_data,wm_data,explain_data)
	
(sm_stages_data,sm_stage_aliases_by_stage,sm_stage_aliases,sm_data,wm_data,explain_data)=initialize_shuffle_calc_json_data(shuffle_calc_json_filename)

async def sm(context, *args, **kwargs):
	if len(sm_data)==0 or len(sm_stages_data)<300 or context["message"].author.bot:return
	selected_stage_index=-1
	selected_strategy=["bhs","btc","cso"]
	show_help=False
	for al in [k.strip().lower().replace(":","") for k in " ".join(args).split(",")]:
		if len(al)==0:continue
		elif al in ["help"]:
			show_help=True
			break
		elif al in ["main"]:selected_strategy=["bhs","btc","cso"]
		elif al in ["all"]:selected_strategy=["bhs","btc","ptc","cso","cth"]
		elif al in ["hs","hammeringstreak","hammering streak"]:selected_strategy=["bhs"]
		elif al in ["tc","typelesscombo","typeless combo"]:selected_strategy=["btc","ptc"]
		elif al in ["so","shotout","shot out"]:selected_strategy=["cso"]
		elif al in ["th","tryhard","try hard","sc","supercheer","super cheer"]:selected_strategy=["cth"]
		elif selected_stage_index<0:
			if len(al)>0 and al==re.sub(r"[^0-9]+","",al):
				psid=int(al)
				if psid>0 and selected_stage_index<300:selected_stage_index=psid-1
			else:
				#possible_stages=difflib.get_close_matches(al,sm_stage_aliases)
				#if len(possible_stages)>0:
				#	best_selected_stage_index=-1
				#	for i,st in enumerate(sm_stage_aliases_by_stage):
				#		if possible_stages[0] in st:
				#			best_selected_stage_index=i
				#			break
				#	if best_selected_stage_index>=0:selected_stage_index=best_selected_stage_index
				query_pokemon = await utils.pokemon_lookup(context, query=args[0])
				if query_pokemon is None:
					return "Unrecognized Pokemon"
				main_stages = [{"Index":k}|v for k,v in yadon.ReadTable(settings.main_stages_table, named_columns=True).items()]
				for main_stage in main_stages:
					if main_stage["Pokemon"].lower() == query_pokemon.lower():
						selected_stage_index = int(main_stage["Index"]) - 1
						break
	if show_help or selected_stage_index==-1:
		txts=["Test accuracy: 10 repeats per move","```Win%  Exp (Std%)  Moves  Team"]
		for strat in sm_data:
			if strat["show"]:
				if len(txts)==5:txts.append("="*32)
				txts.append("{:4.1f}  {:4.0f}  {:4.1f}  {:5.1f}  {}".format(strat["winrate"],float(strat["exp"]),strat["exp_stdm"],strat["moves_left"],strat["team"]))
		txts[-1]+="```"
		await context["koduck"].send_message(context["message"], content="\n".join(txts).strip())
	elif selected_stage_index<0 or selected_stage_index>=300:await context["koduck"].send_message(context["message"], content="Couldn't reverse the SM stage index! :warning:")
	else:
		selected_stage_data=sm_stages_data[selected_stage_index]
		txts=["Stage **{:d}**: **{}** ({:.1f}% encounter)".format(selected_stage_index+1,selected_stage_data["aliases"][0].title(),selected_stage_data["encounter"]),"```Strategy  Moves Std%    Range-68%    Range-95%"]
		for strat in selected_strategy:
			tmega=""
			if strat[0]=="b":tmega="Bee"
			elif strat[0]=="p":tmega="Pin"
			elif strat[0]=="c":tmega="MCX"
			else:tmega="Mega"
			team_name="{}-{}".format(tmega,strat[1:].upper())
			txts.append("{:8.8}  {:5.2f}  {:3.0f}  {:4.1f} ~ {:4.1f}  {:4.1f} ~ {:4.1f}".format(team_name,max(1.,selected_stage_data["results"][strat][0]),
			100.*selected_stage_data["results"][strat][2]/selected_stage_data["results"][strat][0],
			max(1.,selected_stage_data["results"][strat][0]-selected_stage_data["results"][strat][2]),
			selected_stage_data["results"][strat][0]+selected_stage_data["results"][strat][2],
			max(1.,selected_stage_data["results"][strat][0]-2*selected_stage_data["results"][strat][2]),
			selected_stage_data["results"][strat][0]+2*selected_stage_data["results"][strat][2]))
		txts[-1]+="```"
		await context["koduck"].send_message(context["message"], content="\n".join(txts).strip())

async def wm(context,*args,**kwargs):
	if len(wm_data)==0 or context["message"].author.bot:return
	txts=["Moves used: **15** (*+5 price not applied*)","```Coins Std%  Team"]
	for strat in wm_data:
		if strat["show"]:txts.append("{:d}  {:4.1f}  {}".format(strat["coins15m"],strat["std"],strat["team"]))
	txts[-1]+="```"
	await context["koduck"].send_message(context["message"], content="\n".join(txts).strip())

async def explain(context,*args,**kwargs):
	from_dm=context["message"].guild is None
	if len(explain_data.keys())==0 or context["message"].author.bot:return
	question=[k.strip().lower().replace(":","") for k in " ".join(args).split(",")+["help"]][0]
	if question in explain_data.keys():txt=explain_data[question].replace("@","\n")
	else:txt="Usage: **explain argument**. Valid arguments are: {}\nFor more details, visit the Advanced Game Mechanics guide: https://www.reddit.com/r/PokemonShuffle/comments/bdvau1/advanced_game_mechanics/".format(", ".join(list(sorted([k for k in explain_data.keys()]))))
	await context["koduck"].send_message(context["message"], content=txt)

if __name__ == "__main__":sobble_obj.loop.run_until_complete(sobble_obj.start(bot_key))
