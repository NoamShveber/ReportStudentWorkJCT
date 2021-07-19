import datetime
import time
import warnings
import PySimpleGUI as sg
import keyring
import requests

# region consts
headers = {'user-agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/67.0.3396.99 '
                         'Safari/537.36'}
vpnLoginUrl = 'https://lev.jct.ac.il/dana-na/auth/url_1/login.cgi'
studentWorkLoginUrl = 'https://lev.jct.ac.il/,DanaInfo=student-work.jct.ac.il,SSL,dom=1,CT=sxml+login'
attendanceUrl = 'https://lev.jct.ac.il/students/,DanaInfo=student-work.jct.ac.il,SSL+attendance'
fetchEmploymentsUrl = 'https://lev.jct.ac.il/students/attendance/,DanaInfo=student-work.jct.ac.il,SSL,dom=1,CT=sxml+employee'

data = {'tz_offset': '',
        'realm': 'ACAD',
        'fakeusernameremembered': '',
        'fakepasswordremembered': '',
        'username': '',
        'password': ''
        }

secData = {
    'username': '',
    'password': '',
    'stayConnected': 'on'}
# endregion

warnings.filterwarnings("ignore")
sg.theme('DarkAmber')


# Returns in format of hours, minutes
def parseHour(hourStr):
    if hourStr == '':
        return True

    try:
        hours = int(hourStr[0:2])
        minutes = int(hourStr[3:5])
        if hours > 24 or hours < 0 or minutes > 60 or minutes < 0:
            return None

        return hours, minutes

    except ValueError:
        return None


def parseDate(dateStr):
    try:
        d = datetime.datetime(day=int(dateStr[:2]), month=int(dateStr[3:5]), year=int(dateStr[6:]))
        twentyOnethOfMonth = datetime.datetime.now().replace(month=datetime.datetime.now().month - 1, day=21)

        if d > datetime.datetime.now() or d < twentyOnethOfMonth:
            return None

        return d

    except ValueError:
        return None


def postAReport(username, password, employmentID, workDate, beginTime1, endTime1, beginTime2, endTime2, comment):
    data['username'] = username
    data['password'] = password
    secData['username'] = username
    secData['password'] = password

    s = requests.Session()
    r = s.post(vpnLoginUrl, data=data, headers=headers, verify=False)

    # In case it's already connected, need to continue the current session.
    if 'Continue will result in termination of the other session.' in r.text:
        index1 = r.text.find('<input id="DSIDFormDataStr" type="hidden" name="FormDataStr" value="') + 68
        index2 = r.text[index1:].find('"')
        continueSessionData = {
            'btnContinue': 'Continue the session',
            'FormDataStr': r.text[index1:index1 + index2]
        }
        s.post(vpnLoginUrl, data=continueSessionData, headers=headers, verify=False)

    s.post(studentWorkLoginUrl, data=secData, headers=headers, verify=False)

    timeStamp = int(time.time() * 1000)

    reportUrl = 'https://lev.jct.ac.il/students/attendance/,DanaInfo=student-work.jct.ac.il,SSL,dom=1,' \
                'CT=sxml+save?workDate=' + workDate + '&employmentID=' + employmentID + \
                '&workHourID=undefined&cache=' + str(timeStamp)

    reportDict = {
        'IsTariffForAcademicHW': 'False',
        'beginTime1': beginTime1,
        'beginTime2': beginTime2,
        'comment': comment,
        'employmentID': employmentID,
        'endTime1': endTime1,
        'endTime2': endTime2,
        'travels': "",
        'workDate': workDate
    }

    reportResp = s.post(reportUrl, json=reportDict, headers=headers, verify=False)
    sg.popup_ok(eval(reportResp.text.replace('true', 'True'))['message'])


def fetchEmployments(username, password):
    data['username'] = username
    data['password'] = password

    secData['username'] = username
    secData['password'] = password

    s = requests.Session()

    r = s.post(vpnLoginUrl, data=data, headers=headers, verify=False)

    # In case it's already connected, need to continue the current session.
    if 'Continue will result in termination of the other session.' in r.text:
        index1 = r.text.find('<input id="DSIDFormDataStr" type="hidden" name="FormDataStr" value="') + 68
        index2 = r.text[index1:].find('"')
        continueSessionData = {
            'btnContinue': 'Continue the session',
            'FormDataStr': r.text[index1:index1 + index2]
        }
        r = s.post(vpnLoginUrl, data=continueSessionData, headers=headers, verify=False)

    s.post(studentWorkLoginUrl, data=secData, headers=headers, verify=False)

    r3 = s.get(attendanceUrl, headers=headers, verify=False)
    index1 = r3.text.find('$scope.employeeID = Number( ') + 29
    index2 = r3.text[index1:].find(' )')
    employeeID = int(r3.text[index1:index1 + index2 - 1])

    payload = {'employeeID': employeeID}

    r4 = s.post(fetchEmploymentsUrl, headers=headers, json=payload, verify=False)
    employmentList = eval(r4.text.replace('true', 'True'))['items']
    employmentNames = []
    employmentIDs = []

    for emp in employmentList:
        employmentNames.append(emp['fullName'])
        employmentIDs.append(str(emp['id']))

    fetched = dict(zip(employmentNames, employmentIDs))
    keyring.set_password("test", "employments", str(fetched))
    return fetched


def usernameAndPassword():
    global emplDict, username, password
    credLayout = [[sg.Image("icon.png")],
                  [sg.Text(':שם משתמש')],
                  [sg.InputText(key='username', size=(30, 5), justification='center')],
                  [sg.Text(':סיסמה')],
                  [sg.InputText(key='password', justification='center', password_char='*', size=(30, 5))],
                  [sg.Button("התחברות", bind_return_key=True)]]

    # Create the credWindow
    credWindow = sg.Window("JCTReportWork", credLayout, icon="icon.ico", element_justification='c', font='Heebo')

    while True:
        event, values = credWindow.read()
        # End program if user closes credWindow or
        # presses the התחברות button
        if event == "התחברות":
            break

        if event == sg.WIN_CLOSED:
            exit(-1)

    # print("username is: ", values['username'], '\npassword is: ', values['password'])
    credWindow.close()

    try:
        emplDict = fetchEmployments(values['username'], values['password'])
        keyring.set_password("test", 'username', values['username'])
        keyring.set_password("test", values['username'], values['password'])

    except:
        sg.popup_ok("שם משתמש וסיסמא אינם נכונים")
        usernameAndPassword()


def main():
    if keyring.get_password("test", 'username') is None or keyring.get_password("test", 'username') == 'None':
        usernameAndPassword()

    emplDict = eval(keyring.get_password("test", "employments"))

    username = keyring.get_password("test", 'username')
    password = keyring.get_password("test", username)

    layout = [[sg.Text(username + " :שם משתמש")],
              [sg.Button("החלף משתמש")],
              [sg.Text(':מעסיק')],
              [sg.Combo(list(emplDict), key="employmentsCombo", readonly=True), sg.Button("רענן")],
              [sg.Text(':תאריך')],
              [sg.In(key='-cal-', enable_events=True, visible=False),
               sg.CalendarButton('בחר תאריך', format='%d.%m.%Y', close_when_date_chosen=True, locale='he_IL', key='cal',
                                 target='-cal-')],
              [sg.Text('שעת התחלה 1: (חובה)')],
              [sg.InputText(key='beginTime1', size=(30, 5), justification='center')],
              [sg.Text('שעת סיום 1: (חובה)')],
              [sg.InputText(key='endTime1', size=(30, 5), justification='center', )],
              [sg.Text(':שעת התחלה 2')],
              [sg.InputText(key='beginTime2', size=(30, 5), justification='center', )],
              [sg.Text(':שעת סיום 2')],
              [sg.InputText(key='endTime2', size=(30, 5), justification='center', )],
              [sg.Text(':הערות')],
              [sg.InputText(key='comment', size=(30, 5), justification='center', )],
              [sg.Button("שמירה", bind_return_key=True)]]

    repWindow = sg.Window("JCTReportWork", layout, icon="icon.ico", element_justification='c', font='Heebo')

    while True:
        event, values = repWindow.read()

        if event == "החלף משתמש":
            repWindow.close()
            usernameAndPassword()
            main()

        if event == "רענן":
            emplDict = fetchEmployments(username, password)
            repWindow['employmentsCombo'].update(values=list(emplDict))

        if event == '-cal-':  # Update the text on the button
            repWindow['cal'].update(text=repWindow['-cal-'].get())

        if event == "שמירה":
            # Validation:
            if repWindow['employmentsCombo'].get() == '':
                sg.popup_ok('.נא לבחור מעסיק')
                continue

            if repWindow['-cal-'].get() == '' or not parseDate(repWindow['-cal-'].get()):
                sg.popup_ok('.נא לבחור תאריך תקין, בין ה21 בחודש שעבר ל21 בחודש הנוכחי')
                continue

            if repWindow['beginTime1'].get() == '' or not parseHour(repWindow['beginTime1'].get()) or \
                    repWindow['endTime1'].get() == '' or not parseHour(repWindow['endTime1'].get()) or \
                    not parseHour(repWindow['beginTime2'].get()) or not parseHour(repWindow['endTime2'].get()):
                sg.popup_ok('HH:MM נא להזין שעה תקינה בפורמט')
                continue
            break

        if event == sg.WIN_CLOSED:
            exit(-1)

    # Everything is valid
    employmentName = repWindow['employmentsCombo'].get()
    workDate = repWindow['-cal-'].get()
    beginTime1 = repWindow['beginTime1'].get()
    beginTime2 = repWindow['beginTime2'].get()
    endTime1 = repWindow['endTime1'].get()
    endTime2 = repWindow['endTime2'].get()
    comment = repWindow['comment'].get()

    postAReport(username=username, password=password, employmentID=emplDict[employmentName], workDate=workDate,
                beginTime1=beginTime1, endTime1=endTime1, beginTime2=beginTime2, endTime2=endTime2, comment=comment)

    repWindow.close()
    main()


if __name__ == '__main__':
    main()
