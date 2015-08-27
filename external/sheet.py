import httplib2
# Do OAuth2 stuff to create credentials object
from oauth2client.file import Storage
from oauth2client.client import flow_from_clientsecrets
from oauth2client import tools
import gspread
import os

def local_file(name):
    cdir = os.path.dirname(__file__)
    filename = os.path.join(cdir, file)
    return filename

def get_worksheet(i):
    storage = Storage(local_file("creds.dat"))
    credentials = storage.get()
    if credentials is None or credentials.invalid:
        flags = tools.argparser.parse_args(args=[])
        flow = flow_from_clientsecrets(local_file("client_secret.json"), scope=["https://spreadsheets.google.com/feeds"])
        credentials = tools.run_flow(flow, storage, flags)
    if credentials.access_token_expired:
        credentials.refresh(httplib2.Http())
    gc = gspread.authorize(credentials)

    wks = gc.open_by_key('144fuYSOgi8md4n2Ezoj9yNMi6AigoXrkHA9rWIF0EDw')
    return wks.get_worksheet(i)

def get_scheduler_sheet():
    return get_worksheet(0)

def get_testing_sheet():
    return get_worksheet(3)

def get_custom_sheet(*args):
    try:            # Format = cust_<name>_i<index>
        if len(args) > 0:
            idx = int(args[0].split("_")[-1][1:])
            return get_worksheet(5+idx)
        else:
            return get_worksheet(4)
    except:
        print " >> ERROR: malformed custom sheet parameter, returning base custom"
        return get_worksheet(4)

def get_block_sheet():              ## NOTE: Only to be used by blockList.py
    return get_worksheet(5)

actionAlpha = 'I'
idAlpha = 'J'
linkAlpha = 'K'

def updateId(id, row, *arg):
    print 'inside updateId, ', id, row
    cell = idAlpha+str(row + 2)
    worksheet = get_scheduler_sheet()
    worksheet.update_acell(cell, id)
    if len(arg) > 0:
        worksheet.update_acell(actionAlpha+str(row+2), arg[0])

def updateLink(id, link):
    updateAux(id, linkAlpha, link)

def updateAction(id, action):
    updateAux(id, actionAlpha, action)

def updateAux(id, col, data):
    worksheet = get_scheduler_sheet()
    val = worksheet.get_all_records()
    for x in val:
        try:
            if int(id) == int(x['ID']):
                rowNum = val.index(x) + 2
                cell = col+str(rowNum)
                print cell
                worksheet.update_acell(cell, str(data))
        except:
            print "Some error came"

def getFileLink(id):
    worksheet = get_scheduler_sheet()
    val = worksheet.get_all_records()
    for x in val:
        if int(id) == int(x['ID']):
            return x['Data Link']
    return ''
