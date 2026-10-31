import QtQuick
import Quickshell
import Quickshell.Wayland

// Separate RAM-session panel: Labwc exposes minimized windows through wlr-foreign-toplevel.
ShellRoot {
    PanelWindow {
        anchors { bottom: true; left: true; right: true }
        implicitHeight: 60
        exclusiveZone: 60
        color: "#17212b"
        WlrLayershell.namespace: "j86-window-bar"
        WlrLayershell.keyboardFocus: WlrKeyboardFocus.None
        Flickable {
            anchors.fill: parent
            anchors.margins: 6
            contentWidth: windows.width
            clip: true
            flickableDirection: Flickable.HorizontalFlick
            Row {
                id: windows
                spacing: 6
                Repeater {
                    model: ToplevelManager.toplevels
                    Rectangle {
                        required property var modelData
                        width: 166
                        height: 48
                        radius: 8
                        color: modelData.activated ? "#345465" : "#263440"
                        border.color: modelData.minimized ? "#d7b56d" : "#637582"
                        Text {
                            anchors.fill: parent
                            anchors.margins: 10
                            color: "#f1f4f6"
                            verticalAlignment: Text.AlignVCenter
                            elide: Text.ElideRight
                            text: (modelData.minimized ? "↓ " : "") + (modelData.title || modelData.appId || "Window")
                            font.pixelSize: 16
                        }
                        TapHandler {
                            onTapped: {
                                modelData.minimized = false
                                modelData.activate()
                            }
                        }
                    }
                }
                Text {
                    visible: ToplevelManager.toplevels.values.length === 0
                    height: 48
                    text: "Open apps appear here"
                    color: "#c4ced4"
                    verticalAlignment: Text.AlignVCenter
                    font.pixelSize: 16
                }
            }
        }
    }
}
