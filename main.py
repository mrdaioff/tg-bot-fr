import time
import json
import telebot
import random
import schedule
import names
import threading
from datetime import datetime

BOT_TOKEN = '7840046869:AAGjzXrt_KTYOsBcUvSw4_6gPQ4ojiJ0QFY'
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

class DatabaseManager:
    def __init__(self, filename='utilisateurs.json'):
        self.filename = filename
        self.lock = threading.Lock()
        
    def save_data(self, data):
        with self.lock:
            try:
                with open(self.filename, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                return True
            except Exception as e:
                print(f"Erreur lors de l'enregistrement: {str(e)}")
                return False

    def load_data(self):
        with self.lock:
            try:
                with open(self.filename, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            except (FileNotFoundError, json.JSONDecodeError):
                data = self.get_initial_data()
                self.save_data(data)
            return data

    def get_initial_data(self):
        return {
            'solde': {},
            'portefeuille': {},
            'vérification': {},
            'référés': {},
            'référé_par': {},
            'retrait': {},
            'utilisateurs': {},  # New structure for user tracking
            'total_historique': 0,  # Total historical unique users
            'dernière_mise_à_jour': datetime.now().isoformat()
        }

    def update_user(self, user_id, username, first_name):
        data = self.load_data()
        user_str = str(user_id)
        
        # Initialize user data if not exists
        if user_str not in data['utilisateurs']:
            data['utilisateurs'][user_str] = {
                'id': user_id,
                'username': username,
                'first_name': first_name,
                'date_première_visite': datetime.now().isoformat(),
                'dernière_activité': datetime.now().isoformat()
            }
            data['total_historique'] += 1
            
            # Initialize other necessary fields
            data['solde'][user_str] = data['solde'].get(user_str, 0)
            data['portefeuille'][user_str] = data['portefeuille'].get(user_str, "none")
            data['vérification'][user_str] = data['vérification'].get(user_str, 0)
            data['référés'][user_str] = data['référés'].get(user_str, 0)
            data['retrait'][user_str] = data['retrait'].get(user_str, 0)
        else:
            # Update last activity
            data['utilisateurs'][user_str]['dernière_activité'] = datetime.now().isoformat()
            
        self.save_data(data)
        return data

# Initialize database manager
db = DatabaseManager()

def envoyer_statistiques():
    data = db.load_data()
    total_users = data['total_historique']
    total_withdrawals = sum(data['retrait'].values())
    total_referrals = sum(data['référés'].values())
    
    message_stats = f"""
📊 *Statistiques du Jour* :

👥 *Total d'utilisateurs uniques* : {total_users}
💸 *Total des retraits* : {total_withdrawals:,} FCFA
👥 *Total des référencements* : {total_referrals}
    """
    bot.send_message(OWNER_ID, message_stats, parse_mode="Markdown")

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
        user_id = message.chat.id
        user = str(user_id)
        
        # Update user data
        data = db.update_user(
            user_id,
            message.from_user.username,
            message.from_user.first_name
        )

        # Extract referrer ID if provided
        refid = message.text.split()[1] if len(message.text.split()) > 1 else None
        
        if not vérifier_abonnement(user_id):
            markup = telebot.types.InlineKeyboardMarkup()
            for canal in CHANNELS:
                markup.add(telebot.types.InlineKeyboardButton(text=f'Rejoindre {canal}', url=f'https://t.me/{canal.strip("@")}'))
            markup.add(telebot.types.InlineKeyboardButton(text='🤼‍♂️ Vérifier', callback_data='vérifier'))
            
            msg_start = "*🍔 Pour utiliser ce bot, rejoignez ces chaînes :*\n\n"
            for canal in CHANNELS:
                msg_start += f"➡️ {canal}\n"
            bot.send_message(user_id, msg_start, parse_mode="Markdown", reply_markup=markup)
        else:
            menu(user_id)

            # Update referrer data if applicable and not already processed
            if refid and refid != user and data['référé_par'].get(user, None) != refid:
                ref_id = str(refid)
                data['solde'][ref_id] = data['solde'].get(ref_id, 0) + Par_référencement
                data['référés'][ref_id] = data['référés'].get(ref_id, 0) + 1
                data['référé_par'][user] = refid
                db.save_data(data)
                bot.send_message(ref_id, f"*🏧 Félicitations pour votre nouvel invité, Vous avez reçu : +{Par_référencement} FCFA*", parse_mode="Markdown")

    except Exception as e:
        bot.send_message(message.chat.id, "Une erreur est survenue. Veuillez réessayer plus tard.")
        bot.send_message(OWNER_ID, f"Erreur dans /start: {str(e)}")

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
        data = db.load_data()
        
        if call.data == 'vérifier':
            if vérifier_abonnement(user_id):
                bot.answer_callback_query(call.id, text='✅ Vous avez rejoint avec succès ! Vous pouvez maintenant gagner de l\'argent.')
                bot.delete_message(user_id, call.message.message_id)
                
                # Récupérer l'utilisateur qui a parrainé (si applicable)
                ref_par = data['référé_par'].get(user_id)
                
                if ref_par and ref_par != user_id:
                    ref_id = str(ref_par)
                    # Mise à jour du solde du parrain
                    data['solde'][ref_id] = data['solde'].get(ref_id, 0) + Par_référencement
                    # Incrémentation du nombre de référencés
                    data['référés'][ref_id] = data['référés'].get(ref_id, 0) + 1
                    bot.send_message(ref_id, f"*🏧 Félicitations pour votre nouvel invité, Vous avez reçu : +{Par_référencement} FCFA*", parse_mode="Markdown")
                
                # Sauvegarder les changements
                db.save_data(data)
                menu(user_id)
            else:
                bot.answer_callback_query(call.id, text='❌ Vous n\'avez pas vérifié.')
                # Renvoi du message pour vérifier l'abonnement
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
        data = db.load_data()

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

            db.save_data(data)

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
            user_name_bot = "@PayfluxSup_BOT"
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
                db.save_data(data)
                bot.send_message(user_id, f"*Votre compte de retrait a été configuré avec succès sur {data['portefeuille'][user]}*", parse_mode="Markdown")
                user_state.pop(user_id)

            elif state['état'] == 'saisie_montant':
                try:
                    montant_à_retirer = int(message.text)
                    solde = data['solde'].get(user, 0)
                    
                    if montant_à_retirer <= solde:
                        data['solde'][user] -= montant_à_retirer
                        db.save_data(data)
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
    données_utilisateur = db.load_data()
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
    schedule.every(random.randint(7, 53)).minutes.do(envoyer_message_paiement)
    
    # Immediately call the function to send a message right after scheduling
    envoyer_message_paiement()

# Planification de l'envoi de messages de paiement aléatoires
def envoyer_message_paiement():
    identifiant_compte = ''.join([str(random.randint(0, 9)) for _ in range(10)])
    nom_utilisateur = names.get_first_name('fr')
    montant_reçu = random.randint(60, 107) * 500
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
    
    try:
        bot.send_photo('@PayfluxRetraits', photo=url_image, caption=message, parse_mode='Markdown')
    except Exception as e:
        print(f"Erreur lors de l'envoi du message de paiement: {str(e)}")

def planifier_message_aleatoire():
    schedule.every(random.randint(7, 53)).minutes.do(envoyer_message_paiement)
    
    # Immediately call the function to send a message right after scheduling
    envoyer_message_paiement()

def run_schedule():
    while True:
        schedule.run_pending()
        time.sleep(1)

def main():
    # Initialize scheduler
    planifier_message_aleatoire()
    schedule.every().day.at("11:20").do(envoyer_statistiques)

    # Start scheduler thread
    schedule_thread = threading.Thread(target=run_schedule)
    schedule_thread.daemon = True
    schedule_thread.start()

    # Start bot polling with error handling
    while True:
        try:
            print("Bot démarré...")
            bot.polling(none_stop=True, timeout=60)
        except Exception as e:
            print(f"Erreur de polling: {str(e)}")
            time.sleep(10)

if __name__ == '__main__':
    main()
