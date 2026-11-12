import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from supabase import create_client, Client
import os
from flask import Flask
import threading
import time 
import io 

# ================= 1. የመረጃ መቀበያ =================
BOT_TOKEN = "9296969504:AAGsg7ncwkfMV6Mn2eFs7JQLJXm3gJoMmJ4"
SUPABASE_URL = "https://rlkpxelwewazvtghqhhd.supabase.co"
SUPABASE_KEY = "sb_publishable_aCQcrqUsaGytogTK0Kom5g_yhmSjXKP"

VIP_GROUP_LINK = "https://t.me/+yQdJM7LxN8VmNWY0" 
SAMPLE_GROUP_LINK = "https://t.me/+39Ut1OlTHvdjYmQ0"

FREE_GROUP_ID = -1002492184485
STORAGE_GROUP_ID = -1004465909658
ADMIN_IDS = [6183608197, 8937172663]

bot = telebot.TeleBot(BOT_TOKEN)
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
app = Flask(__name__)

# ================= 2. ዳታቤዝ =================
def get_user(user_id):
    res = supabase.table("users").select("*").eq("user_id", user_id).execute()
    if len(res.data) > 0:
        return res.data[0]
    else:
        new_user = {"user_id": user_id, "download_count": 0, "is_vip": False, "referred_count": 0}
        try:
            supabase.table("users").insert(new_user).execute()
        except:
            pass
        return new_user

def alert_admins(user_name, user_id, action):
    for admin in ADMIN_IDS:
        try:
            safe_name = str(user_name).replace("[", "").replace("]", "")
            bot.send_message(admin, f"🔔 **የምዝገባ እንቅስቃሴ!**\n\n👤 ተማሪ: [{safe_name}](tg://user?id={user_id})\n🎯 ምን እያደረገ ነው? : {action}", parse_mode="Markdown")
        except:
            pass

# ================= 3. የአድሚን ፓኔል =================
@bot.message_handler(commands=['admin', 'stats'], func=lambda message: message.from_user.id in ADMIN_IDS and message.chat.type == 'private')
def admin_panel(message):
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("📊 ሪፖርት ማያ 📈", callback_data="admin_stats"),
        InlineKeyboardButton("💾 ተጠቃሚዎችን አውርድ", callback_data="admin_download_users"),
        InlineKeyboardButton("📝 ጥያቄ (Quiz) 🎯", callback_data="admin_quiz"),
        InlineKeyboardButton("📢 ወደ ግሩፕ ላክ 📌", callback_data="admin_broadcast_group"),
        InlineKeyboardButton("📩 ለተጠቃሚዎች ላክ 🚀", callback_data="admin_broadcast_users"),
        InlineKeyboardButton("🔔 Follow-up (ማሳሰቢያ) ላክ ⏳", callback_data="admin_broadcast_followup")
    )
    bot.send_message(message.chat.id, "👨‍💻 **የአድሚን መቆጣጠሪያ ፓኔል:**\n\nምን ማድረግ ይፈልጋሉ?", reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data.startswith("admin_"))
def handle_admin_actions(call):
    if call.from_user.id not in ADMIN_IDS: return
        
    if call.data == "admin_stats":
        bot.send_chat_action(call.message.chat.id, 'typing')
        try:
            res = supabase.table("users").select("*").execute()
            all_users = res.data
            total_users = len(all_users)
            vip_users = sum(1 for u in all_users if u.get('is_vip'))
            free_users = total_users - vip_users
            
            msg = (f"📊 **የቦቱ አጠቃላይ መረጃ (Stats)** 📊\n\n"
                   f"👥 **ጠቅላላ የጀመሩ ተማሪዎች:** {total_users}\n"
                   f"🌟 **ክፍያ ፈፅመው የገቡ (VIP):** {vip_users}\n"
                   f"⏳ **እያሰቡ ያሉ (Free):** {free_users}")
            bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text=msg, parse_mode="Markdown")
        except Exception as e:
            bot.answer_callback_query(call.id, f"⚠️ Error: {e}", show_alert=True)
            
    elif call.data == "admin_download_users":
        bot.answer_callback_query(call.id, "ፋይሉ እየተዘጋጀ ነው...")
        try:
            res = supabase.table("users").select("*").execute()
            users = res.data
            content = "Remedial Matrix Bot - Users List\n"
            content += "="*40 + "\n"
            content += "User ID\t\tStatus\t\tDownloads\n"
            content += "-"*40 + "\n"
            for u in users:
                status = "VIP" if u.get('is_vip') else "Free"
                content += f"{u['user_id']}\t\t{status}\t\t{u['download_count']}\n"
                
            file_stream = io.BytesIO(content.encode('utf-8'))
            file_stream.name = "Remedial_Users_List.txt"
            bot.send_document(call.message.chat.id, file_stream, caption="📁 **የጠቅላላ ተጠቃሚዎች ዝርዝር**")
        except Exception as e:
            bot.send_message(call.message.chat.id, f"⚠️ ፋይሉን ማዘጋጀት አልተቻለም: {e}")

    elif call.data == "admin_quiz":
        msg = bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text="📝 **ጥያቄዎን ይፃፉ:**\n\nበመጀመሪያ ጥያቄውን፣ በመቀጠል ደግሞ ምርጫዎቹን ከፊት ለፊታቸው ሰረዝ (-) በማድረግ ይፃፉ።", parse_mode="Markdown")
        bot.register_next_step_handler(msg, process_quiz_broadcast)
        
    elif call.data == "admin_broadcast_group":
        msg = bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text="📢 **ወደ ግሩፕ ማስታወቂያ ይላኩ:**\n\nማንኛውንም ፅሁፍ አሁን ቢልኩልኝ ዋናው ግሩፕ ላይ **Pin 📌** አደርገዋለሁ።", parse_mode="Markdown")
        bot.register_next_step_handler(msg, process_group_broadcast)

    elif call.data == "admin_broadcast_users":
        msg = bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text="📩 **ወደ ተጠቃሚዎች Inbox ይላኩ:**\n\nማንኛውንም ፅሁፍ አሁን ቢልኩልኝ ለሁሉም ተማሪዎች እልካለሁ!", parse_mode="Markdown")
        bot.register_next_step_handler(msg, process_user_broadcast)
        
    elif call.data == "admin_broadcast_followup":
        markup = InlineKeyboardMarkup(row_width=1)
        markup.add(
            InlineKeyboardButton("📌 ላክ እና Inbox ላይ Pin አድርገው", callback_data="followup_pin"),
            InlineKeyboardButton("📤 ያለ Pin ዝም ብለህ ላክ (Normal)", callback_data="followup_nopin")
        )
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text="⏳ **ማሳሰቢያ (Follow-up) መላኪያ**\n\nመልዕክቱ ሲላክ ተማሪዎቹ Inbox ላይ Pin ይደረግ ወይስ አይደረግ?", reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data in ["followup_pin", "followup_nopin"])
def trigger_followup(call):
    if call.from_user.id not in ADMIN_IDS: return
    should_pin = True if call.data == "followup_pin" else False
    bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text="⏳ **ማሳሰቢያውን በመላክ ላይ ነኝ...**\n\nእባክዎ ትንሽ ይጠብቁ።", parse_mode="Markdown")
    threading.Thread(target=send_followup_broadcast, args=(call.message.chat.id, should_pin)).start()

def send_followup_broadcast(admin_chat_id, should_pin):
    try:
        res = supabase.table("users").select("*").eq("is_vip", False).execute()
        free_users = res.data
        success, failed = 0, 0
        for u in free_users:
            user_id = u['user_id']
            try:
                chat_info = bot.get_chat(user_id)
                first_name = chat_info.first_name if chat_info.first_name else "ውድ ተማሪ"
                
                msg = (f"👋 ሰላም **{first_name}**፣\n\n"
                       "እስካሁን ድረስ ቦቱን አስጀምረው የተለያዩ ነገሮችን አይተዋል፤ የ Sample መመልከቻ ግሩፕም ገብተው በጥቂቱም ቢሆን ትምህርት የምንሰጥበትን መንገድ ተመልክተዋል።\n\n"
                       "ስለዚህ አሁን ከፍለው ወደ ዋናው የ VIP መማሪያ ክላስ መግባት አለብዎት! 🎯")
                
                markup = InlineKeyboardMarkup(row_width=1)
                markup.add(
                    InlineKeyboardButton("💳 ከፍለው ወደ ዋናው tutorial አሁኑኑ ለመግባት እኔን ይጫኑ", callback_data="pay_now"),
                    InlineKeyboardButton("👀 Sample video መመልከቻ group 🎥", callback_data="sample_reminder"),
                    InlineKeyboardButton("❓ ለመክፈል ምን ምን እንደሚያስፈልግ ለማወቅ", callback_data="pay_now")
                )
                
                sent_msg = bot.send_message(user_id, msg, reply_markup=markup, parse_mode="Markdown")
                if should_pin:
                    try: bot.pin_chat_message(user_id, sent_msg.message_id)
                    except: pass
                success += 1
                time.sleep(0.1) 
            except:
                failed += 1
                
        pin_status = "📌 (ከነ Pin)" if should_pin else "📤 (ያለ Pin)"
        bot.send_message(admin_chat_id, f"✅ **የ Follow-up ስርጭት ተጠናቋል {pin_status}!** 🚀\n\n🟢 የደረሳቸው: {success}\n🔴 የከለከሉ: {failed}")
    except Exception as e:
        bot.send_message(admin_chat_id, f"⚠️ ዳታቤዙን በማንበብ ላይ ችግር: {e}")

@bot.callback_query_handler(func=lambda call: call.data == "sample_reminder")
def handle_sample_reminder(call):
    bot.answer_callback_query(call.id, "⚠️ ማሳሰቢያ:\n\nይህ Sample እንጂ ዋናው tutorial አይደለም!\n\nJoin ካደረጉ በኋላ ቪዲዮዎቹ በ Topic መልክ ተዘርዝረው ይቀመጡልዎታል።", show_alert=True)
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("✅ Sample ግሩፑን ተቀላቀል 💎", url=SAMPLE_GROUP_LINK))
    bot.send_message(call.from_user.id, "👇 ወደ Sample ግሩፕ ለመግባት ይሄንን ይጫኑ፦", reply_markup=markup)

def process_user_broadcast(message):
    if message.text and message.text.startswith('/'): return
    bot.send_message(message.chat.id, "⏳ በመላክ ላይ ነኝ...")
    try:
        res = supabase.table("users").select("user_id").execute()
        users = res.data
        success, failed = 0, 0
        for u in users:
            try:
                bot.copy_message(u['user_id'], message.chat.id, message.message_id)
                success += 1
                time.sleep(0.1)
            except: failed += 1
        bot.send_message(message.chat.id, f"✅ **ስርጭቱ ተጠናቋል!** 🚀\n\n🟢 የደረሳቸው: {success}\n🔴 የከለከሉ: {failed}")
    except Exception as e:
        bot.send_message(message.chat.id, f"⚠️ Error: {e}")

def process_group_broadcast(message):
    if message.text and message.text.startswith('/'): return
    try:
        sent_msg = bot.copy_message(FREE_GROUP_ID, message.chat.id, message.message_id)
        bot.pin_chat_message(FREE_GROUP_ID, sent_msg.message_id)
        bot.send_message(message.chat.id, "✅ **ማስታወቂያው ወደ ዋናው ግሩፕ ተልኮ Pin 📌 ተደርጓል!**")
    except Exception as e:
        bot.send_message(message.chat.id, f"⚠️ Error: {e}")

def process_quiz_broadcast(message):
    if message.text and message.text.startswith('/'): return
    lines = message.text.split('\n')
    question = ""
    options = []
    for line in lines:
        if line.strip().startswith('-'): options.append(line.strip()[1:].strip())
        else: question += line + "\n"
    if not options:
        bot.send_message(message.chat.id, "⚠️ **ስህተት:** ምርጫዎቹን አላገኘሁም። ሰረዝ (-) ይጠቀሙ።")
        return
        
    bot_info = bot.get_me()
    bot_link = f"https://t.me/{bot_info.username}?start=quiz"
    markup = InlineKeyboardMarkup(row_width=1)
    for opt in options: markup.add(InlineKeyboardButton(text=f"🔘 {opt}", url=bot_link))
    try:
        sent_msg = bot.send_message(chat_id=FREE_GROUP_ID, text=f"📝 **የዛሬ ጥያቄ (Quiz):**\n\n{question.strip()}\n\n👇 **መልሱን ለመመለስ ከታች ያሉትን ምርጫዎች ይንኩ!**", reply_markup=markup, parse_mode="Markdown")
        bot.pin_chat_message(FREE_GROUP_ID, sent_msg.message_id)
        bot.send_message(message.chat.id, "✅ **ጥያቄው በ Poll መልክ ተልኮ Pin 📌 ተደርጓል!**")
    except Exception as e:
        bot.send_message(message.chat.id, f"⚠️ Error: {e}")

# ================= 6. መግቢያ እና ሽያጭ (Sales Funnel) =================
@bot.message_handler(commands=['start'], func=lambda message: message.chat.type == 'private')
def start_funnel(message):
    user_id = message.from_user.id
    first_name = message.from_user.first_name
    user_data = get_user(user_id)
    args = message.text.split()
    
    if user_data.get('is_vip'):
        bot.send_message(user_id, f"👋 ሰላም የ Remedial Matrix VIP ተማሪ! ወደ ክላሱ ለመግባት ይህንን ሊንክ ይጠቀሙ፦\n{VIP_GROUP_LINK}")
        return

    if len(args) > 1 and args[1] == 'quiz':
        try: bot.send_dice(user_id, emoji='🎯'); bot.send_chat_action(user_id, 'typing'); time.sleep(1.5)
        except: pass
        intro_msg = (f"🎉 **በጣም ጎበዝ {first_name}! አሪፍ ሙከራ ነው!**\n\n"
                     "በትምህርትህ ላይ እንደዚህ አይነት ብዙ ጥያቄዎችን፣ የ Remedial Matrix ሞዴል ፈተናዎችን እና "
                     "አጫጭር ማብራሪያዎችን ማግኘት ትፈልጋለህ?\n\n")
    else:
        try: bot.send_dice(user_id, emoji='🎲'); bot.send_chat_action(user_id, 'typing'); time.sleep(1.5)
        except: pass
        intro_msg = (f"👋 ሰላም **{first_name}**! እንኳን ወደ **Remedial Matrix** በደህና መጣህ!\n\n"
                     "የ Remedial ትምህርት እና የፈተና ጊዜው አጭር በመሆኑ ብዙ ተማሪዎች ይጨነቃሉ። "
                     "ነገር ግን ትክክለኛውን የጥናት መንገድ ከተከተልክ በቀላሉ ማለፍ ትችላለህ!\n\n")
                     
    bot.send_chat_action(user_id, 'typing')
    time.sleep(1)

    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("🧬 Natural Science 🟢", callback_data="stream_natural"),
        InlineKeyboardButton("🌍 Social Science 🟡", callback_data="stream_social")
    )
    bot.send_message(user_id, intro_msg + "እስኪ መጀመሪያ ልወቀህ... የትኛውን Stream ነህ የምትማረው? 👇", reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data.startswith("stream_"))
def handle_stream_choice(call):
    user_id = call.from_user.id
    stream = call.data.split("_")[1]
    
    alert_admins(call.from_user.first_name, user_id, f"Stream መርጧል ({stream}) 📚")
    bot.send_chat_action(user_id, 'typing')
    time.sleep(1.5)
    
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("🎁 VIP ፓኬጁን አሳየኝ 🌟", callback_data="show_package"))
    
    if stream == "natural":
        msg = ("በጣም አሪፍ! 🧬 **Natural Science** ላይ በተለይ Physics እና Math ፈተናዎች ብዙ ተማሪዎችን ሲፈትኑ ይታያሉ።\n\n"
               "ግን አትጨነቅ! እኛ ጋ የሁሉንም ትምህርቶች (Math, Physics, Chemistry, Biology, English) "
               "ውስብስብ ጥያቄዎች እንዴት በቀላሉ መስራት እንደምትችል የምናሳይበት ልዩ ዘዴ አለን።\n\n"
               "ወደ VIP ክላሳችን ምን ምን እንዳዘጋጀንልህ ማየት ትፈልጋለህ?")
    else:
        msg = ("በጣም አሪፍ! 🌍 **Social Science** ላይ ሰፊ ንባብ የሚፈልጉት History፣ Geography እና በተለይ Mathematics "
               "ብዙ ተማሪዎችን ሲፈትኑ ይታያሉ።\n\n"
               "ግን አትጨነቅ! እኛ ጋ የሁሉንም ትምህርቶች (History, Geography, Math, English) "
               "ዋና ዋና ነጥቦች እና የፈተና አሰራር ስልቶችን የምናሳይበት ልዩ ዘዴ አለን።\n\n"
               "ወደ VIP ክላሳችን ምን ምን እንዳዘጋጀንልህ ማየት ትፈልጋለህ?")
               
    bot.edit_message_text(chat_id=user_id, message_id=call.message.message_id, text=msg, reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data == "show_package")
def show_vip_package(call):
    user_id = call.from_user.id
    alert_admins(call.from_user.first_name, user_id, "የ VIP ጥቅሞችን እያነበበ ነው... 🎁")
    bot.send_chat_action(user_id, 'typing')
    time.sleep(1.5)
    
    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(
        InlineKeyboardButton("👀 ነፃ የ Sample ትምህርቶችን እይ 💎", url=SAMPLE_GROUP_LINK),
        InlineKeyboardButton("💳 አሁኑኑ ልመዝገብ (300 ብር) 🚀", callback_data="request_phone")
    )
    
    msg = ("🏆 **የ Remedial Matrix VIP ክላስ** 🏆\n\n"
           "በክላሳችን ውስጥ ከተመዘገብክ እነዚህን ሁሉ ታገኛለህ፦\n\n"
           "✅ **ከ2015 እስከ 2018 E.C** የነበሩ የ Remedial Matrix ጥያቄዎች እና ሞዴል ፈተናዎች ከነ ሙሉ አሰራራቸው\n"
           "✅ ግልፅ የሆኑ ቪዲዮ ቲቶሪያሎች እና አጫጭር ኖቶች (በአማርኛ ማብራሪያ)\n"
           "✅ ራስህን የምትፈትሽባቸው Worksheets\n"
           "✅ 24/7 የጥያቄ እና መልስ ድጋፍ ከአስተማሪዎች ጋር\n\n"
           "⏱ **የፈተና ጊዜ በፍጥነት እየደረሰ ነው!** ቦታዎች ሳይሞሉ አሁኑኑ ተመዝግበህ ዝግጅትህን ጀምር!\n\n"
           "💰 **የክፍያ መጠን:** 300 ብር ብቻ (ለሙሉ ኮርሱ)")
           
    bot.edit_message_text(chat_id=user_id, message_id=call.message.message_id, text=msg, reply_markup=markup, parse_mode="Markdown")

# ================= 7. አዲሱ የስልክ ቁጥር መቀበያ (Phone Request Flow) =================
@bot.callback_query_handler(func=lambda call: call.data in ["pay_now", "request_phone"])
def request_phone_number(call):
    user_id = call.from_user.id
    alert_admins(call.from_user.first_name, user_id, "ክፍያ ለመፈፀም ስልክ ቁጥር እየተጠየቀ ነው... 📱")
    
    try:
        # የድሮውን መልዕክት ማጥፋት
        bot.delete_message(chat_id=user_id, message_id=call.message.message_id)
    except:
        pass
        
    bot.send_chat_action(user_id, 'typing')
    time.sleep(1)
    
    # ስልክ ቁጥር መጠየቂያ ኪቦርድ መላክ
    markup = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.add(KeyboardButton("📱 ስልክ ቁጥር አጋራ (Share Phone Number)", request_contact=True))
    
    msg = ("✅ **ወደ ክፍያ ሰሌዳ ለማለፍ:**\n\n"
           "እባክዎ ትክክለኛ ተማሪ መሆንዎን ለማረጋገጥ ከታች ያለውን **'📱 ስልክ ቁጥር አጋራ'** የሚለውን ቁልፍ ይጫኑ።")
    bot.send_message(user_id, msg, reply_markup=markup, parse_mode="Markdown")

@bot.message_handler(content_types=['contact'], func=lambda message: message.chat.type == 'private')
def handle_contact_and_show_payment(message):
    user_id = message.from_user.id
    phone_number = message.contact.phone_number
    first_name = message.from_user.first_name
    
    # 1. ስልኩን ለአድሚኖች መላክ
    for admin in ADMIN_IDS:
        try:
            bot.send_message(admin, f"📱 **አዲስ ተማሪ ለመክፈል ተዘጋጅቷል!**\n\n👤 ስም: [{first_name}](tg://user?id={user_id})\n📞 ስልክ: `{phone_number}`", parse_mode="Markdown")
        except:
            pass
            
    bot.send_chat_action(user_id, 'typing')
    time.sleep(1.5)
    
    # 2. የክፍያ አማራጭ ማሳየት እና የስልክ መላኪያ ኪቦርዱን ማጥፋት (ReplyKeyboardRemove)
    msg = ("💳 **የክፍያ አማራጮች:**\n\n"
           "🔹 **Telebirr:** `0929698365`\n"
           "🔹 **CBE (ንግድ ባንክ):** `1000667301673`\n"
           "🔹 **Account name:** Mubarek Mustefa\n"
           "🔹 **የሚያስተላልፉት:** 300 ብር\n\n"
           "⚠️ **ትኩረት:** ክፍያውን ከፈፀሙ በኋላ የከፈሉበትን **ደረሰኝ (Screenshot)** "
           "ቀጥታ እዚሁ ቦት ላይ ይላኩልን (Upload ያድርጉ)።\n\n"
           "ወዲያውኑ እንዳረጋገጥን የ VIP ክላሱን መግቢያ ሊንክ እንልክልዎታለን! ጀግና ነህ/ነሽ፣ እንጠብቅሃለን! 💪")
           
    bot.send_message(user_id, msg, reply_markup=ReplyKeyboardRemove(), parse_mode="Markdown")

# ================= 8. ደረሰኝ ማረጋገጫ =================
@bot.message_handler(content_types=['photo'], func=lambda message: message.chat.type == 'private' and message.from_user.id not in ADMIN_IDS)
def handle_receipts(message):
    user_id = message.from_user.id
    user_data = get_user(user_id)
    if user_data.get('is_vip'):
        bot.reply_to(message, "✅ እርስዎ አስቀድመው የ VIP አባል ነዎት!")
        return 
        
    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton("✅ Approve 🟢", callback_data=f"approve_{user_id}"),
        InlineKeyboardButton("❌ Reject 🔴", callback_data=f"reject_{user_id}")
    )
    alert_admins(message.from_user.first_name, user_id, "ደረሰኝ (Screenshot) ልኳል! 🧾")
    
    for admin in ADMIN_IDS:
        try:
            bot.send_photo(admin, message.photo[-1].file_id, caption=f"🧾 **አዲስ ክፍያ መጥቷል!**\n\nየተማሪው ID: `{user_id}`\nስም: {message.from_user.first_name}", reply_markup=markup, parse_mode="Markdown")
        except: pass
            
    bot.reply_to(message, "✅ ደረሰኝዎ ደርሶናል! በአጭር ጊዜ ውስጥ አድሚን አይቶ ክፍያውን ሲያረጋግጥ የ VIP ሊንክ ይደርስዎታል። መልካም ቆይታ!")

@bot.callback_query_handler(func=lambda call: call.data.startswith("approve_") or call.data.startswith("reject_"))
def handle_admin_decision(call):
    if call.from_user.id not in ADMIN_IDS: return
    action, student_id = call.data.split("_")
    student_id = int(student_id)
    
    if action == "approve":
        try: supabase.table("users").update({"is_vip": True}).eq("user_id", student_id).execute()
        except: pass
        bot.edit_message_caption("✅ **Approved! (ተረጋግጧል)**", chat_id=call.message.chat.id, message_id=call.message.message_id)
        bot.send_message(student_id, f"🎉 **እንኳን ደስ አሎት!** ክፍያዎ ተረጋግጧል።\n\nወደ VIP ክላስ ለመቀላቀል ይህንን ሊንክ ይጫኑ (ለማንም እንዳያጋሩ)፦\n{VIP_GROUP_LINK}")
    elif action == "reject":
        bot.edit_message_caption("❌ **Rejected! (ውድቅ ተደርጓል)**", chat_id=call.message.chat.id, message_id=call.message.message_id)
        bot.send_message(student_id, "❌ የላኩት ደረሰኝ ትክክል ስላልሆነ ውድቅ ተደርጓል። እባክዎ ትክክለኛ ደረሰኝ ይላኩ።")

# ================= 9. ለአዲስ ተጠቃሚዎች መምሪያ =================
@bot.message_handler(content_types=['text'], func=lambda message: message.chat.type == 'private' and message.from_user.id not in ADMIN_IDS and not message.text.startswith('/'))
def guide_users(message):
    # ኪቦርዱ ላይ ስልክ ቁጥር መላኪያ ካለ ሌላ guide አይላክም
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("🔄 ወደ መጀመሪያ ተመለስ (Start)", callback_data="restart_flow"))
    msg = ("👋 ሰላም! ለቴሌግራም አዲስ ከሆኑ አያሳስብዎትም።\n\n"
           "እባክዎ እዚህ ጋ ዝም ብለው ፅሁፍ ከመፃፍ ይልቅ፣ <b>በመልዕክቱ መጨረሻ ላይ የተላኩልዎትን ቁልፎች (Buttons)</b> ይጫኑ።\n\n"
           "አሊያም ከታች ያለውን አዝራር ነክተው ከመጀመሪያ ይጀምሩ👇")
    bot.reply_to(message, msg, reply_markup=markup, parse_mode="HTML")

@bot.callback_query_handler(func=lambda call: call.data == "restart_flow")
def restart_flow(call):
    bot.delete_message(call.message.chat.id, call.message.message_id)
    bot.send_message(call.from_user.id, "እባክዎ ይህንን ይጫኑ 👉 /start", reply_markup=ReplyKeyboardRemove())

# ================= 10. Web Server =================
@app.route('/')
def home():
    return "Remedial Sales Bot is running perfectly!"

def run_bot():
    bot.infinity_polling()

if __name__ == "__main__":
    threading.Thread(target=run_bot, daemon=True).start()
    port = int(os.environ.get('PORT', 10000))
    app.run(host="0.0.0.0", port=port)
