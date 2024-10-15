import time
import json
import telebot
import random
import schedule
import names
import threading

BOT_TOKEN = '7840046869:AAEWqV_8grKJrpN1nxsTNRSItNF7tpUTX0c'
CHANNELS = ["@PayfluxRetraits", "@payflux2024"]
OWNER_ID = 411645290

# Paramètres financiers
Bonus_quotidien = 500
Retrait_minimum = 30000
Par_référencement = 2000

bot = telebot.TeleBot(BOT_TOKEN)
user_state = {}
montant_retrait_en_attente = {}

liste_pays = ['Côte d\'Ivoire', 'Sénégal', 'Mali', 'Togo', 'Bénin', 'Burkina Faso', 'Niger', 'Guinée']
méthodes_de_paiement = ['Moov Mobile Money', 'MTN Mobile Money', 'Wave', 'Orange Money', 'Airtel Money']
urls_images = [
    'https://ibb.co/p0SpmV3',  # URL fictif : remplacez par une URL d'image valide
]

# ---------- Fonctions d'assistance ------------

def enregistrer_données(data):
    try:
        with open('utilisateurs.json', 'w') as f:
            json.dump(data, f)
    except Exception as e:
        bot.send_message(OWNER_ID, f"Erreur lors de l'enregistrement des données : {str(e)}")

def charger_données():
    try:
        with open('utilisateurs.json', 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        données_initiales = {'solde': {}, 'portefeuille': {}, 'vérification': {}, 'référés': {},
                             'référé_par': {}, 'retrait': {}, 'id': {}, 'total': 0}
        enregistrer_données(données_initiales)
        return données_initiales

def mettre_à_jour_utilisateur(data, user, refid=None):
    data.setdefault('référés', {}).setdefault(user, 0)
    data['total'] += 1
    data.setdefault('référé_par', {})[user] = refid if refid else user
    data.setdefault('vérification', {})[user] = 0
    data.setdefault('solde', {})[user] = 0
    data.setdefault('portefeuille', {})[user] = "none"
    data.setdefault('retrait', {})[user] = 0
    data.setdefault('id', {})[user] = data['total']

def afficher_méthodes_de_paiement(user_id):
    markup = telebot.types.InlineKeyboardMarkup()
    for methode in méthodes_de_paiement:
        markup.add(telebot.types.InlineKeyboardButton(text=methode, callback_data=f"méthode_paiement:{methode}"))
    bot.send_message(user_id, "Sélectionnez votre méthode de paiement :", reply_markup=markup)

def vérifier_abonnement(user_id):
    for canal in CHANNELS:
        try:
            statut = bot.get_chat_member(canal, user_id).status
            if statut == 'left':
                return False
        except Exception:
            return False
    return True

def menu(user_id):
    clavier = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    clavier.row('👩🏻‍🏫 Comment ça Marche')
    clavier.row('🆔 Mon Compte', '🙌🏻 Invitations')
    clavier.row('⚙️ Configurer le Compte de Retrait', '💸 Retrait')
    clavier.row('📑 Canal de Retrait', '🎁 Bonus Quotidien')
    clavier.row('🏢 À propos de Payflux', '👤 Contacter le Support')
    message_bienvenue = """
👋 *Bienvenue sur PAYFLUX* ! 📢

Nous vous offrons l'opportunité de gagner de l'argent tout en aidant à promouvoir nos canaux partenaires ! 💼 C'est simple, rapide et totalement gratuit. Voici comment ça fonctionne :

🔔 *Comment participer ?*

1️⃣ Abonnez-vous aux canaux partenaires 📲 pour accéder à des avantages exclusifs.
2️⃣ Cliquez sur "🙌🏻 Invitations" pour recevoir votre lien d'affiliation unique 🔗 que vous pouvez partager avec vos amis.
3️⃣ Gagnez 2000 FCFA chaque fois qu'une personne s'inscrit et complète la première tâche grâce à votre lien 💸.
4️⃣ Consultez votre solde à tout moment et cumulez vos gains.
5️⃣ Une fois que vous atteignez 30.000 FCFA, vous pouvez demander votre retrait ! 💵

🎁 *BONUS* : Visitez le bot chaque jour pour recevoir votre bonus quotidien de 500 FCFA !

🎯 *C'est simple* : plus vous invitez, plus vous gagnez !

Cliquez sur "🙌🏻 Invitations" pour récupérer votre lien et commencez à gagner dès maintenant 🚀.

    """
    bot.send_message(user_id, message_bienvenue, parse_mode="Markdown", reply_markup=clavier)

# ---------- Gestionnaires du Bot ------------

@bot.message_handler(commands=['start'])
def start(message):
    try:
        user = str(message.chat.id)
        data = charger_données()

        refid = message.text.split()[1] if len(message.text.split()) > 1 else None
        mettre_à_jour_utilisateur(data, user, refid)

        if not vérifier_abonnement(user):
            markup = telebot.types.InlineKeyboardMarkup()
            for canal in CHANNELS:
                markup.add(telebot.types.InlineKeyboardButton(text=f'Rejoindre {canal}', url=f'https://t.me/{canal.strip("@")}'))
            markup.add(telebot.types.InlineKeyboardButton(text='🤼‍♂️ Vérifier', callback_data='vérifier'))
            msg_start = "*🍔 Pour utiliser ce bot, rejoignez ces chaînes :*\n\n"
            for canal in CHANNELS:
                msg_start += f"➡️ {canal}\n"
            bot.send_message(user, msg_start, parse_mode="Markdown", reply_markup=markup)
        else:
            menu(user)
        
        enregistrer_données(data)
    except Exception as e:
        bot.send_message(message.chat.id, "Il y a eu une erreur lors du traitement de cette commande. Veuillez attendre que l'administrateur résolve le problème.")
        bot.send_message(OWNER_ID, f"Le bot a rencontré une erreur : {str(e)}\nCommande : {message.text}")

@bot.callback_query_handler(func=lambda call: call.data.startswith('méthode_paiement:'))
def gérer_selection_méthode_paiement(call):
    try:
        user_id = call.message.chat.id
        méthode_paiement = call.data.split(':')[1]
        user_state[user_id] = {'état': 'saisie_compte', 'méthode_paiement': méthode_paiement}

        bot.send_message(user_id, f"*Vous avez choisi : {méthode_paiement}*\n\nVeuillez entrer les détails de votre compte {méthode_paiement} au format +XXX XXXXXXXXXX :", parse_mode="Markdown")

        bot.delete_message(user_id, call.message.message_id)
    except Exception as e:
        bot.send_message(user_id, "Il y a eu une erreur lors de la sélection de la méthode de paiement.")
        bot.send_message(OWNER_ID, f"Erreur lors de la sélection de la méthode de paiement : {str(e)}")

@bot.callback_query_handler(func=lambda call: True)
def gestionnaire_query(call):
    try:
        user_id = call.message.chat.id
        data = charger_données()
        if call.data == 'vérifier':
            if vérifier_abonnement(user_id):
                bot.answer_callback_query(call.id, text='✅ Vous avez rejoint avec succès ! Vous pouvez maintenant gagner de l\'argent.')
                bot.delete_message(user_id, call.message.message_id)
                ref_par = data['référé_par'].get(user_id, user_id)
                if ref_par != user_id:
                    ref_id = str(ref_par)
                    data['solde'][ref_id] = data['solde'].get(ref_id, 0) + Par_référencement
                    data['référés'][ref_id] += 1
                    bot.send_message(ref_id, f"*🏧 Nouveau Référencement Niveau 1, Vous avez reçu : +{Par_référencement} FCFA*", parse_mode="Markdown")
                enregistrer_données(data)
                menu(user_id)
            else:
                bot.answer_callback_query(call.id, text='❌ Vous n\'avez pas vérifié.')
                markup = telebot.types.InlineKeyboardMarkup()
                for canal in CHANNELS:
                    markup.add(telebot.types.InlineKeyboardButton(text=f'Rejoindre {canal}', url=f'https://t.me/{canal.strip("@")}'))
                markup.add(telebot.types.InlineKeyboardButton(text='🤼‍♂️ Vérifier', callback_data='vérifier'))
                msg_start = "*🍔 Pour utiliser ce bot, rejoignez ces chaînes :*\n\n"
                for canal in CHANNELS:
                    msg_start += f"➡️ {canal}\n"
                bot.send_message(user_id, msg_start, parse_mode="Markdown", reply_markup=markup)
    except Exception as e:
        bot.send_message(call.message.chat.id, "Il y a eu une erreur lors du traitement de cette commande. Veuillez attendre que l'administrateur résolve le problème.")
        bot.send_message(OWNER_ID, f"Le bot a rencontré une erreur : {str(e)}\nDonnées de rappel : {call.data}")

@bot.message_handler(content_types=['text'])
def envoyer_texte(message):
    try:
        user_id = message.chat.id
        user = str(user_id)
        data = charger_données()

        if message.text == '🆔 Mon Compte':
            solde = data['solde'].get(user, 0)
            portefeuille = data['portefeuille'].get(user, "none")
            msg = f'*👮 Utilisateur : {message.from_user.first_name}*\n\n⚙️ Compte : *{portefeuille}*\n\n💸 Solde : *{solde} FCFA*\n\nGagnez plus en invitant plus d\'amis ! 👫 (*2000 FCFA* par personne invitée) 💰\n\nRetrait disponible à partir de *30000 FCFA*. 📲'
            bot.send_message(user_id, msg, parse_mode="Markdown")

        elif message.text == '🙌🏻 Invitations':
            total_ref = data['référés'].get(user, 0)
            nom_bot = bot.get_me().username
            lien_ref = f"https://t.me/{nom_bot}?start={user_id}"
            msg_ref = f"*Voici votre lien de parrainage pour gagner avec PAYFLUX. Copiez-le et partagez-le avec vos amis pour gagner plus d'argent⬇⬇\n\n🔗 Lien de parrainage ⬇️\n{lien_ref}*\n\n" \
                      f"*⏯️ Total des Invitations : {total_ref} Utilisateurs*\n\n" \
                      f"Vous gagnez *2000 FCFA* par personne invitée. 💰\n\n" \
                      f"Vous pouvez demander un retrait à partir de *30 000 FCFA*. 💸"
            bot.send_message(user_id, msg_ref, parse_mode="Markdown")

        elif message.text == '🎁 Bonus Quotidien':
            temps_actuel = time.time()
            dernier_temps_vérification = data['vérification'].get(user, 0)
            temps_depuis_dernière_vérification = temps_actuel - dernier_temps_vérification

            if temps_depuis_dernière_vérification >= 24 * 60 * 60:
                data['solde'][user] = data['solde'].get(user, 0) + Bonus_quotidien
                data['vérification'][user] = temps_actuel
                bot.send_message(user_id, f"Vous avez reçu votre bonus quotidien de {Bonus_quotidien} FCFA.")
            else:
                temps_restant = (24 * 60 * 60) - temps_depuis_dernière_vérification
                heures = int(temps_restant // 3600)
                minutes = int((temps_restant % 3600) // 60)
                bot.send_message(user_id, f"Vous avez déjà réclamé votre bonus aujourd'hui. Revenez dans {heures} heure(s) et {minutes} minute(s).")

            enregistrer_données(data)

        elif message.text == '💸 Retrait':
            solde = data['solde'].get(user, 0)
            if solde < Retrait_minimum:
                bot.send_message(user_id, f"❌ Votre solde est de *{solde}* FCFA.\n\nLe montant minimum de retrait est de *{Retrait_minimum}* FCFA.", parse_mode="Markdown")
            else:
                user_state[user_id] = {'état': 'saisie_montant'}
                bot.send_message(user_id, "🏦 Entrez le montant à retirer.")

        elif message.text == '⚙️ Configurer le Compte de Retrait':
            afficher_méthodes_de_paiement(user_id)

        elif message.text == '👩🏻‍🏫 Comment ça Marche':
            comment_ça_marche = """
Comment utiliser *PAYFLUX* ? 📲

*PAYFLUX* est un moyen simple et efficace de gagner de l'argent tout en partageant nos canaux partenaires. Voici les étapes pour commencer :

1️⃣ Cliquez sur "/start" dès que vous rejoignez PAYFLUX.  
2️⃣ Abonnez-vous aux canaux qui vous seront présentés.  
3️⃣ Recevez votre lien d'affiliation unique et partagez-le avec vos amis et contacts en cliquant sur "🙌🏻 Invitations".
4️⃣ Gagnez 2000 FCFA à chaque fois qu'une personne s'inscrit et complète la première tâche en utilisant votre lien.  
5️⃣ Consultez votre solde à tout moment via le bot et demandez un retrait lorsque vous atteignez 30.000 FCFA !  

🎯 Plus vous invitez, plus vous gagnez. C'est aussi simple que ça !

*FAQ - Foire aux questions* ❓

1️⃣ *Comment puis-je m'assurer que je suis bien abonné aux canaux requis ?*
Après avoir cliqué sur "/start", le bot vous demandera de vous abonner aux canaux partenaires. Il vérifiera automatiquement si vous êtes bien abonné avant de passer à l'étape suivante.

2️⃣ *Comment fonctionne le lien d'affiliation ?*
Chaque utilisateur reçoit un lien d'affiliation unique dès qu'il s'abonne aux canaux. Ce lien vous permet d'inviter des amis. Chaque fois qu'une personne rejoint PAYFLUX via votre lien et termine les étapes d'inscription, vous recevez 2000 FCFA.

3️⃣ *Quand puis-je demander un retrait ?*
Vous pouvez demander un retrait dès que votre solde atteint 30.000 FCFA. Le bot vous proposera alors différentes méthodes de retrait.

4️⃣ *Comment puis-je consulter mon solde ?*
Vous pouvez consulter votre solde à tout moment en cliquant sur le bouton "🆔 Mon Compte".

5️⃣ *Que se passe-t-il si mon invité ne termine pas l'inscription ?*
Pour recevoir votre récompense de 2000 FCFA, votre invité doit s'abonner aux canaux et compléter les étapes demandées. Si l'invité ne termine pas l'inscription, vous ne recevrez pas la récompense.

6️⃣ *Quels sont les moyens de retrait disponibles ?*
Les moyens de retrait incluent Wave, Mobile Money, Moov Money, Orange Money, Airtel Money, et d'autres options qui vous seront présentées lorsque vous atteindrez le seuil de retrait.

7️⃣ *Mon compte peut-il être banni ?*
Les comptes qui tentent de frauder ou de contourner le système pourront être bannis de manière permanente de PAYFLUX. Respectez les règles et invitez honnêtement des utilisateurs.

Pour toutes autres préoccupations vous pouvez contacter le support client en cliquant sur le bouton "👤 Contacter le Support".
            """
            bot.send_message(user_id, comment_ça_marche, parse_mode="Markdown")



        elif message.text == '📑 Canal de Retrait':
            lien_canal = "https://t.me/PayfluxRetraits"
            bot.send_message(user_id, f"Accédez au canal de retrait en suivant ce lien : {lien_canal}")

        elif message.text == '👤 Contacter le Support':
            user_name_bot = "@SupportPayflux"
            bot.send_message(user_id, f"Contactez le support via le chatbot ici : {user_name_bot}")

        elif message.text == '🏢 À propos de Payflux':
            à_propos_payflux = (
                "🏢 *À propos de Payflux*\n\n"
                "PAYFLUX est une initiative innovante qui vise à permettre à nos utilisateurs de gagner de l'argent tout en aidant à promouvoir les chaînes de nos partenaires. "
                "Nous croyons en la puissance du marketing participatif et désirons offrir des opportunités économiques modernes et flexibles à notre communauté.\n\n"
                "Notre mission est de créer une plateforme simple, sécurisée et bénéfique pour tous. Avec PAYFLUX, chaque membre a la possibilité de tirer parti de son réseau en partageant des liens d'affiliation "
                "et en étant récompensé pour ses efforts.\n\n"
                "🔍 *Notre Vision* :\n"
                "Créer une communauté où chacun peut être récompensé pour sa contribution au réseau grandissant de nos partenaires, tout en découvrant de nouveaux contenus et services intéressants.\n\n"
                "🔗 *Rejoignez-nous* :\n"
                "Si vous avez des questions ou avez besoin d'assistance, notre équipe de support est prête à vous aider à chaque étape. Votre succès est notre priorité.\n\n"
                "Merci de faire partie de PAYFLUX!\n\n"
                "— *L’équipe PAYFLUX* 🤝"
            )
            bot.send_message(user_id, à_propos_payflux, parse_mode="Markdown")

        elif user_id in user_state:
            state = user_state[user_id]
            if state['état'] == 'saisie_compte':
                infos_compte = message.text.strip()
                data['portefeuille'][user] = f"{state['méthode_paiement']}: {infos_compte}"
                enregistrer_données(data)
                bot.send_message(user_id, f"*Votre compte de retrait a été configuré avec succès sur {data['portefeuille'][user]}*", parse_mode="Markdown")
                user_state.pop(user_id)

            elif state['état'] == 'saisie_montant':
                try:
                    montant_à_retirer = int(message.text)
                    solde = data['solde'].get(user, 0)
                    
                    if montant_à_retirer <= solde:
                        data['solde'][user] -= montant_à_retirer
                        enregistrer_données(data)
                        envoyer_message_retrait(user_id, montant_à_retirer)
                        bot.send_message(user_id, "🎉 Votre retrait a été traité avec succès !")
                    else:
                        bot.send_message(user_id, "🔻 Solde insuffisant pour ce montant de retrait.")
                    
                    user_state.pop(user_id)
                except ValueError:
                    bot.send_message(user_id, "Veuillez entrer un nombre valide pour le montant de retrait.")
    except Exception as e:
        bot.send_message(message.chat.id, "Il y a eu une erreur lors du traitement de cette commande. Veuillez attendre que l'administrateur résolve le problème.")
        bot.send_message(OWNER_ID, f"Le bot a rencontré une erreur : {str(e)}\nDonnées du message : {message.text}")

def envoyer_message_retrait(user_id, montant):
    données_utilisateur = charger_données()
    portefeuille_utilisateur = données_utilisateur['portefeuille'].get(str(user_id), "Compte inconnu")
    message = f"🔔 *Demande de Retrait Réussie*\n\n👤 *Utilisateur* : {user_id}\n💰 *Montant* : {montant} FCFA\n🏦 *Compte* : {portefeuille_utilisateur}"
    for canal in CHANNELS:
        bot.send_message(chat_id=canal, text=message, parse_mode='Markdown')

# Planification de l'envoi de messages de paiement aléatoires
def envoyer_message_paiement():
    identifiant_compte = ''.join([str(random.randint(0, 9)) for _ in range(10)])
    nom_utilisateur = names.get_first_name('fr')
    montant_reçu = random.randint(60, 107) * 500
    méthode_paiement = random.choice(méthodes_de_paiement)
    pays = random.choice(liste_pays)
    url_image = random.choice(urls_images)

    message = f"""💰 *Nouveau Paiement PAYFLUX*

🌐 *Statut* : Payé ✅
🌐 *ID Compte* : `{identifiant_compte}`
🌐 *Nom d'utilisateur* : {nom_utilisateur}
🌐 *Montant Reçu* : {montant_reçu:,} FCFA
🌐 *Adresse de Retrait* : Confidentiel 🔐
🌐 *Pays* : {pays}

Bot : [@PayfluxBOT](t.me/PayfluxBOT)

Gagnez en toute confiance et sécurité avec Payflux. 🛡️
Payflux : Monétisez votre répertoire. 💰
    """
    
    bot.send_photo('@PayfluxRetraits', photo=url_image, caption=message, parse_mode='Markdown')

def planifier_message_aleatoire():
    schedule.every(random.randint(3, 35)).minutes.do(envoyer_message_paiement)
    
    # Immediately call the function to send a message right after scheduling
    envoyer_message_paiement()

if __name__ == "__main__":
    planifier_message_aleatoire()
    bot_thread = threading.Thread(target=lambda: bot.polling(none_stop=True))
    bot_thread.start()

    while True:
        schedule.run_pending()
        time.sleep(1)
