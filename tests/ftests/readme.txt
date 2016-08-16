
Few notes on running the Xively Client functional tests
=======================================================

When prerequisites are met, simply run the functional tests by executing the following script in the terminal
    ./xi_ftests


Prerequisites
-------------
    1) Python 3.4+
        If you use brew you can install Python3.4+ by
            brew install python3

            Or you can download it from the official website:
            https://www.python.org/downloads/

    2) Pytest module for Python3
        The trick here is that you can only install pytest for Python2.7 from its official website:
        http://pytest.org/latest/getting-started.html

        If you installed Python3 in step 1), you can install the pytest module for Python3 with the following command:
            pip3 install pytest

        More details about installing pytest under Python3 can be found here:
        http://stackoverflow.com/questions/14371156/pytest-and-python-3
    
    3) Tornado for WebSockets
        In order to install the tornado library please use the following command:
            pip3 install tornado

Please note that most Linux distributions an OSX versions is supplied with Python 2.7. Replacing Python 2.7 is strongly
discouraged as Python3 is not backward compatible. But it is not a real problem for us, because Python 2.7 and
Python 3.4+ can live together in perfect harmony.


Test Case Naming Convention
---------------------------

Purpose of proper naming is to help reader to locate the malfunctioning part as fast as possible just by reading test case name of the failing test.

Underscore separates different parts of the name.
Use camelCase to emphasis new word.

Prefix must be 'test' to make pytest able to find test case function.

This is it:

==============================================================================================================================
test_[ FUNCTION_UNDER_TEST ]_[ SUBFUNCTIONALITY_UNDER_TEST | SUBFEATURE_UNDER_TEST ]_[ INPUT_DESCRIPTION ]_[ EXPECTED_RESULT ]
==============================================================================================================================

example:
test_connect_connectionTimeout_gracefulTimeoutHandling
test_connect_connectionTimeout_clientDoesNotCrash
test_connect_connectionTimeout_connectionCallbackIsCalled

test_publish_toNotProvisionedTopic_handlesPubackWithError
test_publish_happyPublish_successWithPUBACK
test_publish_reflexivePublish_receivesMessageSentOnTopicAlreadySubscribedTo

test_rotatingHosts_4Hosts_triesToConnectToFirstTwoThenSuccessOn3rd

test_subscribe_happySubscribe_receivesSUBACK
test_subscribe_highLoad_100Subscriptions_allSUBACKReceivedAndHandled


