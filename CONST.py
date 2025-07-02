"""____________________________________________________

FILENAME: CONST.py
AUTHOR: Guerric PANIS / David SCLAFER
_______________________________________________________

NXP CONFIDENTIAL
Unpublished Copyright (c) 2020 NXP, All Rights Reserved.
_______________________________________________________"""

import wx

program_name            = "S32K3_BASIS_EMC_BCC2X"
version                 = '2.0.5'
complete_name           = '%s_V%s' % (program_name, version)
#complete_name           = program_name

ANALYSER_VERSION        = '1.0.6'
ANALYSER_PATH           = '\..\S32K_BASIS_EMC_Analyser_V' + ANALYSER_VERSION + '\\EMC_ANALYSER.exe'

# Images
IMG_update              = "\img\\update.png"
IMG_start               = "\img\\start.png"
IMG_clean               = "\img\\broom.png"
IMG_sleep               = "\img\\sleep.png"
IMG_wakeup              = "\img\\wakeup.png"
IMG_stop                = "\img\\stop.png"
IMG_go                  = "\img\\go.png"
IMG_new                 = "\img\\new.png"
IMG_del                 = "\img\\delete.png"
IMG_save                = "\img\\save.png"
IMG_result              = "\img\\app2.ico"
IMG_report              = "\img\\report.png"
IMG_doc                 = "\img\\doc.png"
IMG_about               = "\img\\about.png"
LOGO_APP                = "\img\\app.ico"

DOCS_PATH               = '/DOCS/'
CONTEXT_PATH            = '/CONTEXT/'
SETUP_PATH              = '/SETUPS/'
SCRIPT_PATH             = '/SCRIPTS/'
INITS_PATH              = '/INIT.txt'
LOOPS_PATH              = '/LOOP.txt'
HW_PATH                 = '/HARDWARE/'

# Display parameters
DISP_DEFAULT_COLOR      = wx.Colour(220, 220, 220)
DISP_BLUE_COLOR         = wx.Colour(200, 200, 255)
DISP_ORANGE_COLOR       = wx.Colour(255, 200, 150)
DISP_RED_COLOR          = wx.Colour(255, 150, 150)
DISP_GREEN_COLOR        = wx.Colour(200, 255, 200)
DISP_WHITE_COLOR        = wx.Colour(255, 255, 255)
DISP_BLACK_COLOR        = wx.Colour(0, 0, 0)

# Menu size
SIZE_COMBO_COM          = 75
SIZE_COMBO_DEFAULT      = 100
SIZE_GENE_IP_ADDR       = 110
SIZE_COMBO_GPIB_ADDR    = 250
SIZE_COMBO_SETUP        = 172
SIZE_COMBO_IC_TYPE      = 100
SIZE_COMBO_IC_NB        = 50
SIZE_COMBO_IC_PHY       = 70

# Size
CST_SizeTBButtonIcon    = wx.Size(20, 20)
CST_SizeTBButtonIcon2   = wx.Size(25, 25)
CST_SizeTitleIcon       = wx.Size(5, 2)
CST_SizeCheckBox        = wx.Size(17, 17)

MAX_DEVICE_TYPE         = 4
MAX_DEVICE_NB           = 16    # Per chain
MAX_CHAIN_NB            = 6
MAX_DEVICE_PER_TYPE     = MAX_CHAIN_NB * MAX_DEVICE_NB
MAX_DEVICE_ADD          = 63
MAX_CHAIN_ADD           = 6

DISP_DEFAULT_COL_WIDTH  = 82
DISP_PARAM_COL_WIDTH    = 120
DISP_SCRIPT_COL_WIDTH   = 220
DISP_PARAM_OFFSET       = 7
DISP_MAX_COLUMN         = ((MAX_DEVICE_PER_TYPE + 1) * (MAX_DEVICE_TYPE-2)) + 4
TPL_STATUS_NB           = 5     # 5 differents TPL status possible
TPL_STATUS              = ['Echo err', 'No resp', 'Resp err', 'Error', 'Ok']

TPL_ECHO_ERR            = 2
TPL_NO_RESP             = 4
TPL_RESP_ERR            = 8
TPL_ERR                 = 0
TPL_OK                  = 1

#UART_BAUDRATE           = 8_000_000
UART_BAUDRATE            = 921_600

MAX_COM_TIMEOUT         = 1.5   # 1 second
MAX_MICRO_REV           = 10_000
UART_BUFFER_SIZE        = 4094

# Menu IDs
ID_COM_TYPE             = wx.ID_HIGHEST + 4
ID_COM_LIST             = wx.ID_HIGHEST + 5
ID_UART_UPDATE          = wx.ID_HIGHEST + 6
ID_UART_GAUGE           = wx.ID_HIGHEST + 7

ID_GENE_TARGET          = wx.ID_HIGHEST + 8
ID_GENE_COM_TYPE        = wx.ID_HIGHEST + 9
ID_GENE_ADDR            = wx.ID_HIGHEST + 10

ID_GENE_UPDATE          = wx.ID_HIGHEST + 12

ID_SETUP_CAMPAIGN       = wx.ID_HIGHEST + 13
ID_SETUP_CAMPAIGN_TYPE  = wx.ID_HIGHEST + 14
ID_SETUP_UPDATE         = wx.ID_HIGHEST + 15
ID_SETUP_NEW            = wx.ID_HIGHEST + 16
ID_SETUP_DEL            = wx.ID_HIGHEST + 17
ID_SETUP_SAVE           = wx.ID_HIGHEST + 18


ID_START                = wx.ID_HIGHEST + 29
ID_SLEEP                = wx.ID_HIGHEST + 31
ID_WAKEUP               = wx.ID_HIGHEST + 32
ID_STOP                 = wx.ID_HIGHEST + 33

ID_RES                  = wx.ID_HIGHEST + 34

ID_LOG_TRIG             = wx.ID_HIGHEST + 35
ID_LOG_TIMER_VAL        = wx.ID_HIGHEST + 36
ID_LOG_GO               = wx.ID_HIGHEST + 37

ID_NOTEBOOK             = wx.ID_HIGHEST + 38

ID_NEW_SETUP_ENTER      = wx.ID_HIGHEST + 39
ID_NEW_SETUP_OK         = wx.ID_HIGHEST + 40
ID_NEW_SETUP_NOK        = wx.ID_HIGHEST + 41

ID_ABOUT                = wx.ID_HIGHEST + 42
ID_DOC                  = wx.ID_HIGHEST + 43
ID_REPORT               = wx.ID_HIGHEST + 44


# Machine states
STATE_INITIAL           = 1
STATE_REF_DELAY         = 2
STATE_REF               = 3
STATE_ACQ               = 4
STATE_FAIL              = 5
STATE_NEW_ACQ           = 6

# Report
CSV_SEPARATOR           = ','

# Guards
GUARD_HEADER_1          = ['PARAM', 'STOP FAIL', 'TRIG PORT', 'TRIG PIN', 'GUARD DELTA', '', 'GUARD ABS', '', 'DELTA REF']
GUARD_HEADER_2          = ['MIN', 'MAX', 'MIN', 'MAX']
GUARD_STOP              = ['Yes', 'No']
GUARD_TRIG_PORT         = ['', 'PTA', 'PTB', 'PTC', 'PTD', 'PTE']

# General parameters
DELAY_BEFORE_REF        = 3 # In seconds
REF_SAMPLE_NB           = 5
RES_SAMPLE_NB           = 1

SCRIPT_MAX_ID           = 4096 #256
SCRIPT_MAX_FRAME        = 70
FRAME_MAX_LEN           = 100
DISP_PARAMS_NB_MAX      = 200

# Interface choice
UART_INTERFACE          = 0
CAN_INTERFACE           = 1

# PHY 664 EN pin, PTD22
PHY_664_EN_PORT         = 4
PHY_664_EN_PIN          = 22

DISP_SETUP_GRID_OFFSET  = 4
