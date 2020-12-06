import time,pygsheets,threading,gpiozero,config,subprocess,sys
from mfrc522 import SimpleMFRC522
reader = SimpleMFRC522()
print(sys.path)

sys.path.append("/home/pi/AMS")
SCANNING_MODE = 0
TAG_UPDATE = 1
mode = SCANNING_MODE
redLed = gpiozero.LED(config.R_PIN)
redLed.blink(1,1,200)

powerButton = gpiozero.Button(config.POWER_PIN,pull_up=False)
rSwitch = gpiozero.Button(config.ROCKER_RIGHT,pull_up=False)
lSwitch = gpiozero.Button(config.ROCKER_LEFT,pull_up=False)

blueLed = gpiozero.LED(config.B_PIN)
greenLed = gpiozero.LED(config.G_PIN)

def updateStatus():
    global mode
    while True:
        if powerButton.value:
            redLed.blink(.05,.05,20000)
            subprocess.call(['sudo','poweroff'])

        if lSwitch.value:
            mode = TAG_UPDATE
        else:
            mode = SCANNING_MODE

threading.Thread(target=updateStatus).start()

class RFIDTags(threading.Thread):

    isRunning = True

    AMS_FOLDER = '1oHlhnVLu2HBJVwGP1NiVfYgH4c4i1SD6'
    gsheets = pygsheets.authorize(client_secret="client_Secret.json")

    allSheets = gsheets.drive.spreadsheet_metadata("'"+AMS_FOLDER+"'" + " in parents")
    allSheetsName = {}
    for sheet in allSheets:
        allSheetsName[sheet['name']] = sheet['id']

    configSheet = None

    currentYear = time.strftime("%Y")

    if 'Config' in allSheetsName:
        configSheet = gsheets.open_by_key(allSheetsName['Config'])
    else:
        configSheet = gsheets.create('Config',folder=AMS_FOLDER)

    configWorksheetsName = []
    for worksheet in configSheet.worksheets():
        configWorksheetsName.append(worksheet.title)
    print(allSheets)
    print(configWorksheetsName)

    keysSheet = configSheet.worksheet_by_title("Keys")

    uidKeys = {}

    _keys = keysSheet.get_all_values(include_tailing_empty=False,include_tailing_empty_rows=False)

    for index,item in enumerate(_keys):
        if index == 0:
            continue
        uidKeys[item[0]] = item[1]

    print(uidKeys)

    termSheet = None
    if currentYear+"-1" in allSheetsName:
        termSheet = gsheets.open_by_key(allSheetsName[currentYear+'-1'])
    else:
        termSheet = gsheets.create(currentYear+'-1',folder=AMS_FOLDER)

    todaySheet = None
    try:
        todaySheet = termSheet.worksheet_by_title(time.strftime("%d-%m-%Y"))
    except:
        todaySheet = termSheet.add_worksheet(time.strftime("%d-%m-%Y"))
        todaySheet.append_table(["Key", "Name"])

    nameSheet = termSheet.worksheet_by_title('Names')
    _names = nameSheet.get_all_values(include_tailing_empty=False,include_tailing_empty_rows=False)
    names = {}
    for item in _names:
        names[item[0]] = item[1]
    print(names)

    _todayAttendance = todaySheet.get_all_values(include_tailing_empty=False,include_tailing_empty_rows=False)
    todayAttendance = {}

    for attendance in _todayAttendance:
        todayAttendance[attendance[0]] = attendance[1]

    print(todayAttendance)

    def run(self) -> None:
        redLed.on()
        index = len(self.uidKeys)+1
        while self.isRunning:
            print("Hold a tag near the reader")
            id, text = reader.read()
            print("ID: %s\nText: %s" % (id, text))
            if mode == SCANNING_MODE:
                try:
                    if self.uidKeys[str(id)] not in self.todayAttendance:
                        blueLed.on()
                        self.updateTodaySheet(self.uidKeys[str(id)],self.names[self.uidKeys[str(id)]])
                        self.todayAttendance[self.uidKeys[str(id)]] = self.names[self.uidKeys[str(id)]]
                        blueLed.off()
                    else:
                        blueLed.blink(.05,0.05,4)
                except KeyError:
                    pass
            elif mode == TAG_UPDATE:
                print(self.uidKeys)
                if str(id) not in self.uidKeys:
                    greenLed.on()
                    self.updateKeySheet(id,index)
                    self.uidKeys[str(id)] = "Key "+str(index)
                    index += 1
                    greenLed.off()
                else:
                    greenLed.blink(0.05,0.05,4)
            time.sleep(2)


    def updateKeySheet(self,id,index):
        try:
            self.keysSheet.append_table([str(id), "Key " + str(index)])
        except Exception:
            self.updateKeySheet(id,index)


    def updateTodaySheet(self,key,name):
        try:
            self.todaySheet.append_table([key,name])
        except Exception:
            self.updateTodaySheet(key,name)