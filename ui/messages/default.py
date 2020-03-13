# -*- coding: utf-8 -*-

'''
This Source Code Form is subject to the terms of the Mozilla
Public License, v. 2.0. If a copy of the MPL was not distributed
with this file, You can obtain one at http://mozilla.org/MPL/2.0/.
'''

data={
    'titleInstall': u'DWAgent - Installation', 
    'titleUninstall': u'DWAgent - Uninstallation', 
    'welcomeLicense': u'License\nThis software is free and open source.\nIt consists of one main component and several accessory components defined "app" that could be governed by different licenses. For more informations visit: https://www.dwservice.net/en/licenses-sources.html',
    'welcomeSecurity': u'Security\nTo protect your privacy we guarantee that no information will be stored on our servers and communications are encrypted so third parties can\'t read them anyway.',
    'welcomeSoftwareUpdates': u'Software updates\nThe updates of this software are automatic.',
    'confirmUninstall': u'Do you want remove DWAgent?',
    'mustAccept': u'In order to continue, you must select the option {0}',
    'or' : u'or',    
    'accept': u'I accept',
    'decline': u'I do not accept',
    'next': u'Next', 
    'back': u'Back', 
    'yes': u'Yes', 
    'no': u'No', 
    'ok': u'Ok',
    'cancel': u'Cancel', 
    'close': u'Close', 
    'waiting': u'Waiting...', 
    'alreadyInstalled': u'DWAgent already installed.\n\nThe agent automatically updates to the last version. It means that you do not need to manually install newer updates.', 
    'notInstalled': u'DWAgent not installed.', 
    'fieldRequired': u'The field \'{0}\' is required.', 
    'selectPathInstall': u'Select the installation path:',  
    'path': u'Path', 
    'mustSelectOptions': u'You must select an option.', 
    'confirmInstall': u'Do you want install DWAgent to \'{0}\'?', 
    'warningRemovePath': u'Warning the destination folder already exists then it will be deleted.', 
    'pathNotCreate': u'Could not create the folder. Invalid path or permission denied.', 
    'pathCreating': u'Folder creation...', 
    'unexpectedError': u'Unexpected error.\n{0}',
    'downloadFile': u'Downloading file {0}...',
    'copyFiles': u'Copying files...', 
    'installService': u'Installing service...', 
    'installServiceErr': u'Installation service failed.', 
    'uninstallService': u'Uninstalling service...', 
    'startService': u'Starting service...', 
    'startServiceErr': u'Starting service failed.', 
    'installMonitor': u'Installing monitor...', 
    'uninstallMonitor': u'Uninstalling monitor...', 
    'installMonitorErr': u'Installation monitor failed.',
    'monitorStatus': u'Status',
    'monitorConnections': u'Connections',
    'monitorStatusOffline': u'Offline', 
    'monitorStatusOnline': u'Online', 
    'monitorStatusDisabled': u'Disabled', 
    'monitorStatusUpdating': u'Updating', 
    'monitorStatusNoService': u'No service', 
    'monitorShow': u'Show', 
    'monitorHide': u'Hide', 
    'monitorUninstall': u'Uninstall', 
    'monitorConfigure': u'Configure',
    'monitorEnable': u'Enable', 
    'monitorDisable': u'Disable', 
    'monitorErrorConnectionConfig': u'Connection error. Please check if DWAgent service is started.', 
    'monitorDisableAgentQuestion': u'Do you want disable the agent?', 
    'monitorEnableAgentQuestion': u'Do you want enable the agent?', 
    'monitorEnterPassword': u'Enter password:', 
    'monitorInvalidPassword': u'Invalid password.',
    'monitorUninstallNotRun': u'You can not uninstall without root permissions.\nRun the command dwaguninstall into shell.', 
    'monitorTitle': u'DWAgent - Monitor', 
    'monitorAgentDisabled': u'Agent disabled.', 
    'monitorAgentEnabled': u'Agent enabled.', 
    'configureTitle':u'DWAgent - Configuration', 
    'configureChooseOperation':u'Please choose an operation:', 
    'configureAgent':u'Configure agent',
    'configureProxy':u'Configure proxy', 
    'configureMonitor':u'Configure monitor',
    'configurePassword':u'Configure password', 
    'configureSetPassword':u'Set password', 
    'configureRemovePassword':u'Remove password', 
    'configureRemovePasswordQuestion':u'Do you want remove the password?', 
    'configureExit':u'Exit',
    'configureEnd':u'Configuration has been completed.',  
    'configureChangeInstallKey':u'Change installation code', 
    'configureEnableAgent': u'Enable agent', 
    'configureAgentEnabled': u'Agent enabled.', 
    'configureEnableAgentQuestion': u'Do you want enable the agent?', 
    'configureDisableAgent': u'Disable agent', 
    'configureAgentDisabled': u'Agent disabled.', 
    'configureDisableAgentQuestion': u'Do you want disable the agent?', 
    'configureErrorConnection': u'Connection error. Please check if DWAgent service is started.', 
    'configureUninstallKeyQuestion':u'Uninstall the current installation code?', 
    'configureUninstallationKey':u'Uninstallation...', 
    'configureKeyInstalled':u'Key installed succesfully.', 
    'configureProxyEnd':u'Proxy configured successfully.', 
    'configureTrayIconVisibility':u'Tray icon visibility', 
    'configureChooseMonitorTrayIconVisibility':u'Do you want show monitor in tray icon?', 
    'configureTrayIconOK':u'Tray icon visibility, configured successfully.', 
    'configurePasswordErrNoMatch':u'The password are not match.', 
    'configurePasswordUpdated':u'Password updated.', 
    'configureInsertPassword':u'Please insert config password:', 
    'configureInvalidPassword':u'Invalid password.', 
    'installShortcuts': u'Installing shortcuts...', 
    'installShortcutsErr': u'Installation shortcuts failed.', 
    'uninstallShortcuts': u'Uninstalling shortcuts...', 
    'enterInstallCode': u'Enter the installation code', 
    'code': u'Code', 
    'checkInstallCode': u'Checking installation code...', 
    'errorConnectionConfig': u'Connection error. Please check if DWAgent service is started.', 
    'errorInvalidCode': u'The code entered is invalid.', 
    'reEnterCode': u'Re-enter the code', 
    'endInstall': u'Installation has been completed.', 
    'cancelInstall': u'The installation was canceled.', 
    'cancelUninstall': u'The uninstallation was canceled.', 
    'endInstallConfigLater': u'Installation has been completed.\nThe agent has not been configured. You can still proceed with the configuration later.', 
    'errorConnectionQuestion': u'Connection error. Please check your internet connection or firewall configuration.\nDo you want configure proxy?', 
    'noTryAgain': u'No, try again', 
    'configureLater': u'Configure later', 
    'chooseProxyType': u'What proxy type you want to use?', 
    'proxySystem': u'System', 
    'proxyHttp': u'Http', 
    'proxySocks4': u'Socks4', 
    'proxySocks4a': u'Socks4a',
    'proxySocks5': u'Socks5',
    'proxyNone': u'None', 
    'proxyInfo': u'Insert proxy info.', 
    'proxyHost': u'Host', 
    'proxyPort': u'Port', 
    'proxyAuthUser': u'User', 
    'proxyAuthPassword': u'Password', 
    'validInteger':u'The field \'{0}\' must be an integer.', 
    'endUninstall': u'Uninstallation has been completed.', 
    'removeFile': u'Removing file...', 
    'menuUninstall': u'Uninstall', 
    'menuConfigure': u'Configure', 
    'menuMonitor': u'Monitor', 
    'missingRuntime':u'Runtime not found.',
    'missingNative':u'Native not found.', 
    'versionInstallNotValid':u'The version of the installer is not correct for your operating system.\nPlease download the correct version. {0}',     
    'missingInfoFile':u'File info.json not found.',
    'user':u'User',
    'password':u'Password', 
    'rePassword':u'Retype Password', 
    'confirmExit':u'Are you sure you want to exit?', 
    'linuxRootPrivileges':u'You must have root privileges to install DWAgent.\nPlease start the script using the root user.', 
    'windowsAdminPrivileges':u'You must have administrator privileges to install DWAgent.\nPlease start the executable with \'run as administrator.\'', 
    'pressEnter':u'Press enter to continue.', 
    'error':u'Error', 
    'option':u'Option', 
    'optionNotValid':u'Option selected is invalid.', 
    'enter':u'enter', 
    'commands':u'Commands', 
    'toBack':u'to go back.', 
    'toExit':u'to exit.',
    'install':u'Install',
    'runWithoutInstallation':u'Run',
    'runWithoutInstallationStarting':u'Agent startup...',
    'runWithoutInstallationUpdating':u'Agent update...',
    'runWithoutInstallationConnecting':u'Opening session...',
    'runWithoutInstallationOnlineTop':u'The session is active.\nTo connect to this agent go to https://www.dwservice.net',
    'runWithoutInstallationOnlineUser':u'User: {0}',
    'runWithoutInstallationOnlinePassword':u'Password: {0}',
    'runWithoutInstallationOnlineBottom':u'WARNING:\nDo not disclose this information to people you do not trust, otherwise you will allow them access to this agent. So if you are not sure what you are doing, close this application.',
    'runWithoutInstallationWait':u'Wait for the new connection in progress (attempt {0})...',
    'runWithoutInstallationClosing':u'Closing session...',
    'runWithoutInstallationEnd':u'Session ended.',
    'runWithoutInstallationUnexpectedError':u'Unexpected error.\nit was not possible to start DWAgent. If the problem persists, try to download the latest release of DWAgent, delete the folder \'{0}\' and run DWAgent again.',    
    'configureInstallAgent':u'How do you prefer to configure the agent?',
    'configureInstallNewAgent':u'Creating a new agent',
    'configureInstallCode':u'Entering the installation code',
    'createNewAgent':u'Creating agent in progress...',
    'agentName':u'Agent name',
    'enterInstallNewAgent':u'Enter data to create a new agent:',
    'dwsUser':u'DWS user',     
    'dwsPassword':u'DWS password',
    'reEnterData':u'Re-enter the data',
    'errorInvalidUserPassword':u'Invalid user or password.',
    'errorAgentNameNotValid':u'The agent name is not valid. You can not use the characters / \ | # @ : .',
    'errorAgentAlreadyExsists':u'The agent {0} already exists.',
    'errorAgentMax':u'Exceeded maximum number of agents.',
    'enterRunCode': u'Enter the connection code',
    'runWithoutInstallationOnlineTopPutCode':u'The session is active.' ,
    'runWithoutInstallationOnlineBottomPutCode':u'WARNING:\nNow the agent is ready to accept connection. So if you are not sure what are you doing, please close this application.' 
}
