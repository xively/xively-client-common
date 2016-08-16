function ConnectDriver(port)
{

    if ( "WebSocket" in window )
    {

        document.write( "Connecting to test framework : ws://localhost:" + port + "/<br>" );

        var mqttClient = null
        var ctrlClient = new WebSocket( "ws://localhost:" + port + "/" );

        ctrlClient.onopen = ctrlClientOnOpen;
        ctrlClient.onclose = ctrlClientOnClose;
        ctrlClient.onmessage = ctrlClientOnMessage;

        function ctrlClientOnOpen ( )
        {
            document.write( "Connected<br>" );
        };

        function ctrlClientOnClose ( )
        {
            document.write( "Disconnected from test framework<br>" );
        };

        function ctrlClientOnMessage ( event )
        {
            document.write( "Message from test framework : " + event.data + "<br>" );

            var argsobj = JSON.parse( event.data );

            if ( argsobj.command == "CONNECT" )
            {
                document.write( "Connecting to MQTT broker : " + argsobj.address + ":" + argsobj.port + " as " + argsobj.clientid + "<br>" );

                if ( mqttClient == null )
                {
                    mqttClient = new Paho.MQTT.Client( argsobj.address , Number( argsobj.port ) , argsobj.clientid );
                    mqttClient.onConnectionLost = mqttClientOnConnectionLost;
                    mqttClient.onMessageArrived= mqttClientOnMessageArrived;
                }
                mqttClient.connect(
                {
                    userName  : argsobj.username ,
                    password  : argsobj.password ,
                    onSuccess : mqttClientOnConnectionSuccess ,
                    onFailure : mqttClientOnConnectionFailure ,
                    useSSL : argsobj.usessl ,
                    timeout : 60
                } );
            }
            else if ( argsobj.command  == "DISCONNECT" )
            {
                document.write( "Disconnecting from MQTT broker...<br>" );
                mqttClient.disconnect( );
            }
            else if ( argsobj.command  == "SUBSCRIBE" )
            {
                for ( index = 0 ; index < argsobj.topics.length ; index++ )
                {
                    var topic = argsobj.topics[index];
                    document.write( "Subscribing to " + " " + topic + " " + topic[0] + " " + topic[1] + " ...<br>" );
                    var subscribeOptions =
                    {
                        qos : topic[1] ,
                        invocationContext : null ,
                        timeout : 10 ,
                        onSuccess : subscribeOnSuccess ,
                        onFailure : subscribeOnFailure
                    }
                    mqttClient.subscribe( topic[0] , subscribeOptions );
                }
            }
            else if ( argsobj.command  == "UNSUBSCRIBE" )
            {
                document.write( "Unsubscribing from " + argsobj.topic + " ...<br>" );
                var unsubscribeOptions =
                {
                    qos : 0 ,
                    invocationContext : null ,
                    timeout : 10 ,
                    onSuccess : unsubscribeOnSuccess ,
                    onFailure : unsubscribeOnFailure
                }
                mqttClient.unsubscribe( argsobj.topic , unsubscribeOptions );
            }
            else if ( argsobj.command  == "PUBLISH" )
            {
                document.write( "Sending message + " + argsobj.payload + " to " + argsobj.topic + " ...<br>" );
                var message = new Paho.MQTT.Message( argsobj.payload );
                message.destinationName = argsobj.topic;
                mqttClient.send( message );
            }
        };

        function mqttClientOnConnectionSuccess ( )
        {
            document.write( "Connected to MQTT broker<br>" );
            var argsobj =
            {
                'command' : "CONNECTED"
            }
            document.write( "Sending " + JSON.stringify( argsobj ) + "to test framework<br>" );
            ctrlClient.send( JSON.stringify( argsobj ) );
        }

        function mqttClientOnConnectionFailure ( responseObject )
        {
            document.write( "Can't connect to MQTT broker " + responseObject.errorMessage + "<br>" );
            var argsobj =
            {
                'command' : "REJECTED" ,
                'description' : "CAN'T CONNECT TO BROKER : " + responseObject.errorMessage
            }
            document.write( "Sending " + JSON.stringify( argsobj ) + "to test framework<br>" );
            ctrlClient.send( JSON.stringify( argsobj ) );
        }

        function mqttClientOnConnectionLost ( )
        {
            document.write( "Disconnected from MQTT broker<br>" );
            var argsobj =
            {
                'command' : "DISCONNECTED" ,
            }
            document.write( "Sending " + JSON.stringify( argsobj ) + "to test framework<br>" );
            ctrlClient.send( JSON.stringify( argsobj ) );
        }

        function mqttClientOnMessageArrived ( message )
        {
            document.write( "MQTT message arrived " + message.destinationName + " " + message.payloadString + "<br>" );
            var argsobj =
            {
                'command' : "MESSAGE" ,
                'topic' : message.destinationName ,
                'payload' : message.payloadString
            }
            document.write( "Sending " + JSON.stringify( argsobj ) + "to test framework<br>" );
            ctrlClient.send( JSON.stringify( argsobj ) );
        }

        function mqttClientOnMessageDelivered( message )
        {
            document.write( "MQTT message delivered " + message.payloadString + "<br>" );
            var argsobj =
            {
                'command' : "PUBLISHED" ,
                'payload' : message.payloadString
            }
            document.write( "Sending " + JSON.stringify( argsobj ) + "to test framework<br>" );
            ctrlClient.send( JSON.stringify( argsobj ) );
        }


        function subscribeOnSuccess( context )
        {
            document.write( "Subscribe success<br>" );
            var argsobj =
            {
                'command' : "SUBSCRIBED" ,
                'success' : 1 ,
                'description' : "subscribe success"
            }
            document.write( "Sending " + JSON.stringify( argsobj ) + "to test framework<br>" );
            ctrlClient.send( JSON.stringify( argsobj ) );
        }

        function subscribeOnFailure( context )
        {
            document.write( "Subscribe failure" + message.payloadString + "<br>" );
            var argsobj =
            {
                'command' : "SUBSCRIBED" ,
                'success' : 0 ,
                'description' : "subscribe failure"
            }
            document.write( "Sending " + JSON.stringify( argsobj ) + "to test framework<br>" );
            ctrlClient.send( JSON.stringify( argsobj ) );
        }

        function unsubscribeOnSuccess( context )
        {
            document.write( "Unsubscribe success<br>" );
            var argsobj =
            {
                'command' : "UNSUBSCRIBED" ,
                'success' : 1 ,
                'description' : "unsubscribe success"
            }
            document.write( "Sending " + JSON.stringify( argsobj ) + "to test framework<br>" );
            ctrlClient.send( JSON.stringify( argsobj ) );
        }

        function unsubscribeOnFailure( context )
        {
            document.write( "Unsubscribe failure" + message.payloadString + "<br>" );
            var argsobj =
            {
                'command' : "UNSUBSCRIBED" ,
                'success' : 0 ,
                'description' : "unsubscribe failure"
            }
            document.write( "Sending " + JSON.stringify( argsobj ) + "to test framework<br>" );
            ctrlClient.send( JSON.stringify( argsobj ) );
        }

    }
    else
    {
        document.writeln( "WebSocket NOT supported by your Browser!" );
    }
}