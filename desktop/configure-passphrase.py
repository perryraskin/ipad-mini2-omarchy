#!/usr/bin/python3
"""Add a local Show/Hide control without inspecting credential contents."""
import os,pathlib

def patch(text):
 if 'id: j86RevealPassphrase' in text:return text
 start=text.index('      TextField {\n        id: pwField')
 end=text.index('\n      BorderSurface {',start)
 field=text[start:end]
 assert field.count('password: true')==1 and field.count('anchors.right: connectPwBtn.left')==1
 field=field.replace('password: true','password: !passwordPanel.showPassphrase').replace('anchors.right: connectPwBtn.left','anchors.right: j86RevealPassphrase.left')
 button='''
      Rectangle {
        id: j86RevealPassphrase
        visible: pwField.visible
        anchors.right: connectPwBtn.left
        anchors.rightMargin: Style.space(6)
        anchors.verticalCenter: pwField.verticalCenter
        width: 64
        height: 48
        radius: 6
        color: root.passwordText.length ? "#345465" : "#263440"
        Text {
          anchors.centerIn: parent
          text: passwordPanel.showPassphrase ? "Hide" : "Show"
          color: root.bar.foreground
          font.pixelSize: 16
        }
        TapHandler {
          onTapped: {
            passwordPanel.showPassphrase = !passwordPanel.showPassphrase
            pwField.forceActiveFocus()
          }
        }
      }
'''
 text=text[:start]+field+button+text[end:]
 text=text.replace('id: passwordPanel\n','id: passwordPanel\n      property bool showPassphrase: false\n      onVisibleChanged: showPassphrase = false\n',1)
 old='+ pwField.implicitHeight + Style.spacing.rowGap'
 assert text.count(old)==1
 return text.replace(old,'+ Math.max(48, pwField.implicitHeight) + Style.spacing.rowGap',1)

if __name__=='__main__':
 assert os.geteuid()==0
 assert pathlib.Path('/proc/device-tree/model').read_bytes().rstrip(b'\0')==b'Apple iPad mini 2 (Cellular)'
 p=pathlib.Path('/home/tablet/.local/share/omarchy-ipad/shell/plugins/panels/network/Panel.qml')
 before=p.read_text()
 try:after=patch(before)
 except (ValueError,AssertionError):raise SystemExit('Network panel layout changed; Show/Hide patch was not applied')
 if after!=before:p.write_text(after);os.chown(p,1000,1000)
 print('Wi-Fi passphrase Show/Hide control configured')
