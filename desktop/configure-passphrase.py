#!/usr/bin/python3
"""Enlarge the Wi-Fi touch panel and add Show/Hide without reading credentials."""
import os,pathlib

def visibility_patch(text):
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

def patch(text):
 text=visibility_patch(text)
 if '// J86 finger-sized Wi-Fi panel' in text:return text
 edits={
  'contentWidth: panel.fittedContentWidth(Style.space(380))':'contentWidth: panel.fittedContentWidth(Style.space(600))',
  'height: Math.min(contentHeight, Style.space(240))':'height: Math.min(contentHeight, Style.space(360))',
  'implicitHeight: Math.max(networkIcon.implicitHeight, networkInfo.implicitHeight, rightAction.implicitHeight) + Style.spacing.rowPaddingX':'implicitHeight: Math.max(60, Math.max(networkIcon.implicitHeight, networkInfo.implicitHeight, rightAction.implicitHeight) + Style.spacing.rowPaddingX)',
 }
 for old,new in edits.items():
  assert text.count(old)==1,old
  text=text.replace(old,new,1)
 import re
 sizes={'body':18,'bodySmall':16,'caption':16,'subtitle':20,'title':24,'icon':20}
 text=re.sub(r'font.pixelSize: Style.font.(bodySmall|body|caption|subtitle|title|icon)\b',lambda m:'font.pixelSize: Math.max('+str(sizes[m[1]])+', Style.font.'+m[1]+')',text)
 text=text.replace('PanelActionButton {','PanelActionButton {\n        size: 48')
 for field in ('idField','pwField'):
  needle='id: '+field+'\n'
  assert text.count(needle)==1
  text=text.replace(needle,needle+'        implicitHeight: 48\n',1)
 text=text.replace('id: j86RevealPassphrase\n','id: j86RevealPassphrase\n        // J86 finger-sized Wi-Fi panel\n',1)
 text=text.replace('width: 64\n        height: 48','width: 72\n        height: 48',1)
 text=text.replace('spacing: Style.space(4)\n        clip: true','spacing: Style.space(8)\n        clip: true',1)
 return text

if __name__=='__main__':
 assert os.geteuid()==0
 assert pathlib.Path('/proc/device-tree/model').read_bytes().rstrip(b'\0')==b'Apple iPad mini 2 (Cellular)'
 p=pathlib.Path('/home/tablet/.local/share/omarchy-ipad/shell/plugins/panels/network/Panel.qml')
 before=p.read_text()
 try:after=patch(before)
 except (ValueError,AssertionError):raise SystemExit('Network panel layout changed; Show/Hide patch was not applied')
 if after!=before:p.write_text(after);os.chown(p,1000,1000)
 print('Wi-Fi touch panel and Show/Hide configured')
