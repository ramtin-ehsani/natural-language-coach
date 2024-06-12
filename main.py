import google.generativeai as genai
from database import Database
import fitbit
import datetime

gemini_key = 'AIzaSyBrXIpxJM3LyLSAsmSsL0BcWEl99E2dNuQ'
genai.configure(api_key=gemini_key)

model = genai.GenerativeModel('gemini-1.5-flash')

def refresh_cb(token):
    global current_fitbit_client
    access_token = token['access_token']
    refresh_token = token['refresh_token']
    expires_at = token['expires_at']
    db.update_tokens(current_fitbit_client, access_token, refresh_token, expires_at)
    print(token)

def coaching_message():
    global current_fitbit_client

    user = db.get_fitbit_details('0')
    id = user.get('user_id')

    user_id_fitbit = user.get("fitbit_id")
    current_fitbit_client = id

    # FitBit
    fitbit_client = fitbit.Fitbit(
        client_id=user.get('client_id'),
        client_secret=user.get('client_secret'),
        access_token=user.get('access_token'),
        refresh_token=user.get('refresh_token'),
        expires_at=user.get('expires_at'),
        refresh_cb=refresh_cb
    )

    # Get food and nutrition summary
    theday = datetime.date.today()
    start = theday - datetime.timedelta(days=7)
    dates = [start + datetime.timedelta(days=d) for d in range(7)]
    dates = [str(d) for d in dates]
    eaten = {}
    nutrition = {}
    for date in dates:
        url = 'https://api.fitbit.com/1/user/' + user_id_fitbit + '/foods/log/date/' + date + '.json'
        response = fitbit_client.make_request(url)
        summary = response.get('summary')
        nutrition[date] = summary
        foods = response.get('foods')
        food_logs = []
        for food in foods:
            logged = food.get('loggedFood')
            food_logs.append(logged.get('name'))
        if len(food_logs) == 0:
            nutrition.pop(date, None)
        else:
            eaten[date] = food_logs

    nuts = nutrition.values()
    calories = 0
    calories_list = []
    calories_included = []
    for nut in nuts:
        calories_temp = nut.get('calories')
        calories_list.append(calories_temp)
        calories_included.append(calories_temp)
    if len(calories_included) != 0:
        calories = round(sum(calories_included) / len(calories_included), 2)

    # Get Weight logs
    weight_logs = {}
    url = 'https://api.fitbit.com/1/user/' + user_id_fitbit + '/body/log/weight/date/' + dates[0] + '/' + dates[6] + '.json'
    response = fitbit_client.make_request(url)
    response = response.get('weight')
    ws = []
    for log in response:
        bmi = log.get('bmi')
        weight = log.get('weight')
        ws.append(weight)
        date = log.get('date')
        weight_logs[date] = {
            'bmi': bmi,
            'weight': weight
        }
    wc = 0
    wc_message = ''
    start_weight = 200
    if len(weight_logs.values()) >= 2:
        first, *_, last = weight_logs.values()
        start_weight = first.get('weight')
        wc = round(first.get('weight') - last.get('weight'), 2)
    if wc < 0:
        wc_message = str(float(abs(wc))) + 'lb gained'
    elif wc > 0:
        wc_message = str(float(abs(wc))) + 'lb lost'

    weight_average = 'no weights were provided'
    if len(ws) != 0:
        weight_average = round(sum(ws) / len(ws), 2)
    if len(ws) == 0:
        wc_message = 'no weights were provided'

    if weight_average != 'no weights were provided':
        weight_average = str(weight_average) + ' lbs'

    # Get AZM
    url = 'https://api.fitbit.com/1/user/' + user_id_fitbit + '/activities/active-zone-minutes/date/' + dates[0] + '/' + dates[
        6] + '.json'
    response = fitbit_client.make_request(url)
    response = response.get('activities-active-zone-minutes')
    azm = 0
    for log in response:
        activity = log.get('value')
        azm += activity.get('activeZoneMinutes')

    messages = []
    user_texts = db.get_user_texts(id)
    for t in user_texts:
        role = t.get('role')
        text = t.get('text')
        messages.append(
            {"parts": [text], "role": role},
        )
    # print(messages)
    content = (
    "You are a weight loss coach in a behavioral weight loss program. Below is a summary of my goal and "
    "data pattern in the past week:\n"
    "1. Overall Weight Loss: My starting weight was {}lb, and my long-term goal is 180lb.".format(start_weight) + "\n"
    "2. Weight tracking: My goal is to track my weight every day (7 days a week). Over the past 7 days, I have tracked {} days.".format(len(ws)) + "\n"
    "3. Weekly Averaged Weight: My average weight is {} in the past 7 days.".format(weight_average)+"\n"
    "4. Weekly Weight Loss: My weekly goal is to 1-2 lbs per week. My weight change in the past week is {}.".format(wc_message) + "\n"
    "5. Calorie tracking: My goal is to track my food every day (7 days a week). Over the past week, I have tracked {} days in the past week.".format(len(calories_list)) + "\n"
    "6. Calorie intake: My goal is to take in 1800-2000 calories per day. My average calories over the past week is {} calories.".format(calories) + "\n"
    "7. Physical activity: My moderate to vigorous physical activity (MVPA) goal is to exercise 250 minutes per week. My total MVPA minutes over the past week is {} minutes.".format(azm) + "\n"
    "Write a very encouraging and empathetic message for the participant to provide feedback. The message should"
    "be no longer than 5 sentences, and no greeting is needed. The message should use a second-person "
   "pronoun. The message should summarize the data and pattern in the past week. You should praise "
   "and validate what is going well. If weight loss has not occurred in the past 7 days, express your "
   "hypothesis as to why not and provide helpful strategies to address the part that is not going well. If "
   "the hypothesis is that the calorie goal is too high, you should suggest lowering the calorie goal. If "
   "the calorie intake is low and I am not losing 1-2 lbs each week, assume that I am not recording my "
    "calorie intake accurately. If you don’t know my weight change, ask me why I didn’t consistently weigh in "
    "(e.g., avoiding weigh-in) and stress the importance of daily weigh-in. The message should ask Socratic "
   "questions that will invite the participant to reflect on his progress. The message should also ask the "
    "person if the coaching you gave makes sense and if there is anything about his situation that you should "
    "better understand.")
    print(content)
    messages.append({"role": "user", "parts": [content]})
    db.insert_text(id, 'Ramtin', content, 'user')
    response = model.generate_content(messages)
    db.insert_text(id, 'Ramtin', response.text, 'model')
    print(response.text)

DATABASE_PATH = "database.db"
db = Database(DATABASE_PATH)

# db.create_fitbit_details('0', "eyJhbGciOiJIUzI1NiJ9.eyJhdWQiOiIyM1I0TFoiLCJzdWIiOiJCTkpNQlAiLCJpc3MiOiJGaXRiaXQiLCJ0eXAiOiJhY2Nlc3NfdG9rZW4iLCJzY29wZXMiOiJyc29jIHJzZXQgcmFjdCBybG9jIHJ3ZWkgcmhyIHJudXQgcnBybyByc2xlIiwiZXhwIjoxNzE4MjM2ODkyLCJpYXQiOjE3MTgyMDgwOTJ9.3FzMglThmNuA86w4gIs_cabP2E4i71Nrbf38FO6UP_0",
#                          "3575abbf5ff4d8665497597d089aef53f029163d898a761db17148eda741330c", "1718236892.702949", '23R4LZ', '5abc0a8c19157a3dd6ce2c8fcb7173d3', 'BNJMBP')

if __name__ == '__main__':
    print('Talk to Gemini Coach!')
    while True:
        text_input = input()
        if text_input == 'coach message':
            coaching_message()
        else:
            messages = []
            user_texts = db.get_user_texts('0')
            for t in user_texts:
                role = t.get('role')
                text = t.get('text')
                messages.append(
                    {"parts": [text], "role": role},
                )
            # print(messages)
            messages.append(
                {"role": "user", "parts": [text_input]},
            )
            db.insert_text('0', 'Ramtin', text_input, 'user')
            try:
                response = model.generate_content(messages)
                print(response.text)
                db.insert_text('0', 'Ramtin', response.text, 'model')
            except ValueError as e:
                if "requires the response to contain a valid `Part`" in str(e):
                    if hasattr(response, 'candidate') and hasattr(response.candidate, 'safety_ratings'):
                        print("Safety Ratings Issue with the prompt:", response.candidate.safety_ratings)
                    else:
                        print("Safety Ratings Issue with the prompt.")