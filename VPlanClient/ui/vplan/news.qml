import QtQuick 2.0
import QtQuick.Controls 2.0

Page {
    property string nid;
    property string section;
    property string newsText;
    property string img;

    Rectangle {
        id: newsBoxContent
        height: parent.height - newsNav.height
        width: parent.width
        color: "#00000000"
        border.color: "#00000000"

        Rectangle {
            id: newsContainer
            height: parent.height
            width: parent.width
            property string uuid: nid
            color: "#00000000"
            border.color: "#00000000"

            Image {
                id: newsIcon
                source: img
                asynchronous: true
                height: 110
                anchors.leftMargin: 20
                anchors.verticalCenter: parent.verticalCenter
                fillMode: Image.PreserveAspectFit
                anchors.left: parent.left
            }
            Text {
                id: newsContent
                width: parent.width - newsIcon.width - 20 - 25
                height: 174
                anchors.left: newsIcon.right
                anchors.leftMargin: 25
                font.pointSize: 20
                horizontalAlignment: Text.AlignLeft
                verticalAlignment: Text.AlignVCenter
                wrapMode: Text.WordWrap
                text: newsText
                textFormat: Text.AutoText

                Text {
                    id: newsTopic
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
