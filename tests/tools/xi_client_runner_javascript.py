import webbrowser
import json
import os
from tools.xi_websocketserver import XiWebSocketServer
from tools.xi_client_error_codes import XiClientErrorCodes
from tools.xi_mock_broker.xi_mock_broker import cert_reqs, tls_version

#   Install tornado for this testcase :
#       brew install python
#       pip install tornado
#
#   Add self-signed-localhost-cert.pem to keychain, trust it
#   Add self-signed-expired-cert.pem to keychain, untrust it

class XiClientRunnerJavascriptPaho:


    def __init__(self):

        # start control channel

        self.usessl = False
        self.wantsslerror = False
        self.wantcerterror = False

        self.server = XiWebSocketServer( self )

        try:

            self.server.start()

            # write starting html with servers port number

            absolute = "file://" + os.getcwd() + "/../tools/xi_js_driver/xi_client_driver.html"
            relative = "../tools/xi_js_driver/xi_client_driver.html"
            htmlfile = open( relative , 'w+')
            htmlfile.write( '<!DOCTYPE html>\n'
                            '<html>\n'
                            '<head lang="en">\n'
                                '<meta charset="UTF-8">\n'
                                '<title></title>\n'
                                '<script type="text/javascript" src="mqttws31.js"></script>\n'
                                '<script type="text/javascript" src="xi_client_driver.js"></script>\n'
                            '</head>\n'
                            '<body onload="ConnectDriver(' )
            htmlfile.write( str( self.server.address[1] ) )
            htmlfile.write( ')">\n'
                            '</body>\n'
                            '</html>);\n' )
            htmlfile.close()

            # start js driver
            # os.system( "nodejs filename" ) to use node.js later
            # browser = webbrowser.get('safari') to use different browser later
            webbrowser.open( absolute , 0 , False )

            # hold main thread until driver connection
            # main timeout is in xi_ftest_sample act
            while self.server.connected == False:
                pass

        except Exception as inst:

            print( "XiClient_JS init exception:" , inst )


    def __del__(self):

        self.server.stop()

    def stop(self):
        self.server.connected = False

    def join(self, timeout):
        while self.server.connected == True:
            pass
        # TODO: Implement timeout properly
        return True

    def connect(self, server_address, connect_options, connection_timeout):

        argsobj = \
        {
            'command' : "CONNECT" ,
            'address' : server_address[0],
            'username' : "username_js_paho" ,
            'password' : "password_js_paho" ,
            'port' : str( server_address[1] ) ,
            'clientid' : connect_options.client_id ,
            'usessl' : self.usessl
        }
        self.server.message( json.dumps( argsobj ) )

    def on_connect_finish(self, connect_response):

        pass

    def on_connect_reject_tunnel(self, connect_response):

        if self.wantsslerror == True :
            self.on_connect_finish(XiClientErrorCodes.SSLERROR)

        if self.wantcerterror == True :
            self.on_connect_finish(XiClientErrorCodes.CERTERROR)

    def disconnect(self):

        argsobj = \
        {
            'command' : "DISCONNECT"
        }
        self.server.message( json.dumps( argsobj ) )

    def on_disconnect(self, return_code):

        pass

    def subscribe(self, topic_list):

        argsobj = \
        {
            'command' : "SUBSCRIBE" ,
            'topics' : topic_list
        }
        self.server.message( json.dumps( argsobj ) )

    def on_subscribe_finish(self, granted_access_list):

        pass

    def publish(self, topic, message, qos):

        argsobj = \
        {
            'command' : "PUBLISH" ,
            'topic' : topic ,
            'message' : message ,
            'qos' : qos
        }
        self.server.message( json.dumps( argsobj ) )

    def on_publish_finish(self, return_code):

        pass

    def on_message_received(self, topic, message):

        pass

    def setup_tls(self, ca_certs, certfile=None, keyfile=None, require_cert_from_server=cert_reqs, tls_version=tls_version, ciphers=None):

        self.usessl = True

        # we should decode the cert itself and analyze whether it's expired or bad domain

        if "expired" in ca_certs :

            self.wantsslerror = True

        if "bad-domain" in ca_certs :

            self.wantcerterror = True
