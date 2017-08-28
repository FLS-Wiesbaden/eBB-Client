import QtQuick 2.0
import QtQuick.Controls 2.0

Page {
    property string aid;
    property string section;
    property string annoText;
    property string img;

    Rectangle {
        id: annoBoxContent
        height: parent.height - annoNav.height
        width: parent.width
        color: "#00000000"
        border.color: "#00000000"

        Rectangle {
            id: annoContainer
            height: parent.height
            width: parent.width
            property string uuid: aid
            color: "#00000000"
            border.color: "#00000000"

            Image {
                id: annoIcon
                source: img
                asynchronous: true
                height: 110
                anchors.leftMargin: 20
                anchors.verticalCenter: parent.verticalCenter
                fillMode: Image.PreserveAspectFit
                anchors.left: parent.left
            }
            Text {
                id: annoContent
                width: parent.width - annoIcon.width - 20 - 25
                height: 174
                anchors.left: annoIcon.right
                anchors.leftMargin: 25
                font.pointSize: 20
                horizontalAlignment: Text.AlignLeft
                verticalAlignment: Text.AlignVCenter
                wrapMode: Text.WordWrap
                text: annoText
                textFormat: Text.AutoText

                Text {
                    id: annoTopic
                    x: 0
                    width: 168
                    height: 30
                    color: "#999999"
                    text: section
                    anchors.top: parent.top
                    anchors.topMargin: 18
                    anchors.right: parent.right
                    anchors.rightMargin: 10
                    horizontalAlignment: Text.AlignRight
                    font.pixelSize: 17
                }
            }
        }
    }
}
