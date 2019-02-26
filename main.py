import os
import vt
import pam
import time
import signal
import socket
import termios

CLEAR_TERM = b"\x1b[2J\x1b[H"
USER = os.environ["USER"]
HOST = socket.gethostname()
MOTD = os.environ.get("MOTD", "\x1b[1;37m<< \x1b[1;36mpyvtlock \x1b[1;37m>>\x1b[0m\n")

cnr = vt.get_active_console()
cvt = vt.open_console(cnr)
nnr = None
nvt = None
oldmode = None
oldattr = None

def lock_motd():
    nvt.buffer.write(CLEAR_TERM)
    print(MOTD, file = nvt)
    print("{} locked by {}".format(HOST, USER), file = nvt)

def read_pwd(prompt, newline = True):
    print(prompt, end = "", file = nvt)

    data = nvt.readline()
    if data[-1] == "\n":
        data = data[:-1]

    if newline:
        print(file = nvt)

    return data

def lock_iteration():
    lock_motd()
    read_pwd("", False)

    p = pam.pam()
    pwd = read_pwd("Password: ")
    if p.authenticate(USER, pwd):
        return True
    else:
        print("pyvtlock: {}".format(p.reason), file = nvt)
        time.sleep(1.5)
        return False

def lock_loop():
    while not lock_iteration():
        pass

def setup_term():
    global oldattr

    oldattr = termios.tcgetattr(nvt.fileno())
    newattr = termios.tcgetattr(nvt.fileno())
    newattr[3] &= ~termios.ECHO

    termios.tcsetattr(nvt.fileno(), termios.TCSADRAIN, newattr)
    nvt.buffer.write(CLEAR_TERM)

def cleanup_term():
    global oldattr

    termios.tcsetattr(nvt.fileno(), termios.TCSADRAIN, oldattr)
    oldattr = None

    nvt.buffer.write(CLEAR_TERM)

def setup_vt():
    global nnr
    global nvt
    global oldmode

    nnr = 63
    nvt = vt.open_console(nnr)
    setup_term()

    vt.activate(cvt, nnr)

    signal.signal(signal.SIGUSR1, lambda sn, f: vt.reldisp(nvt, False))
    signal.signal(signal.SIGUSR2, lambda sn, f: vt.reldisp(nvt, True))

    oldmode = vt.getmode(nvt)
    newmode = vt.VtMode(vt.VT_PROCESS, 0, signal.SIGUSR1, signal.SIGUSR2, signal.SIGHUP)
    vt.setmode(nvt, newmode)

def cleanup_vt():
    global nnr
    global nvt
    global oldmode
    vt.setmode(nvt, oldmode)
    vt.activate(cvt, cnr)

    signal.signal(signal.SIGUSR1, signal.SIG_DFL)
    signal.signal(signal.SIGUSR2, signal.SIG_DFL)

    cleanup_term()
    nvt.close()

    nnr = None
    nvt = None
    oldmode = None

if __name__ == '__main__':
    cvt = vt.open_console(vt.get_active_console())
    time.sleep(.1)

    setup_vt()
    lock_loop()
    cleanup_vt()

    cvt.close()
