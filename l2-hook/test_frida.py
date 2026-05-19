import frida
import sys
import time

print("START")
sys.stdout.flush()

try:
    session = frida.attach(6068)
    print("ATTACHED")
    sys.stdout.flush()
    
    script = session.create_script('send({type:"test", msg:"hello from Frida"});')
    print("SCRIPT_CREATED")
    sys.stdout.flush()
    
    def on_message(msg, data):
        print("MSG:", msg)
        sys.stdout.flush()
    
    script.on("message", on_message)
    script.load()
    print("LOADED")
    sys.stdout.flush()
    
    time.sleep(3)
    session.detach()
    print("DONE")
except Exception as e:
    print("ERROR:", e)
    sys.stdout.flush()
