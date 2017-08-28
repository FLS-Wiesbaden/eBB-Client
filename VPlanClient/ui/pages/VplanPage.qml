import QtQuick 2.4
import QtGraphicalEffects 1.0
import QtQuick.Controls 2.0
import QtQuick.Window 2.2
import EbbPlanHandler 1.0
import "../../js/vPlanScripts.js" as VPlanScripts

Column {
	id: ebbContainer
	width: parent.width
	height: parent.height
	spacing: 0

	signal hookPresenter()

	property int aCurIdx: -1
	property int aDayIdx: -1
    property int aPageIdx: -1
	property int activModel: 0
	property int aMaxEntries: 0
	property int aMissingEntries: 0
	property bool aPresenterActive: false

	property int aNumPages: 1
	property var aDayList: []
	property var aPlanList: []
	property bool presenterPageAvailable: false
	property bool otherPageAvailable: false

	// Plan sizes...
	property double colClass: 0
	property double colHour: 0
	property double colOriginal: 0
	property double colChange: 0

    /*Component.onCompleted: {
        VPlanScripts.createDefaultAnnouncement()
    }*/

	EbbPlanHandler {
		id: ebbPlanHandler
		objectName: "ebbPlanHandler"

		onConnected: {
			console.log('I\'m connected now!')
			ebbContainer.loadPrimaryData()
            VPlanScripts.vplanConnected()
		}
		onDisconnected: {
            VPlanScripts.vplanDisconnected()
		}
		onReset: {
			aDayList = []
            aPlanList = []
            VPlanScripts.clearAnnouncements()
            VPlanScripts.clearNews()
		}
		onSuspendTv: {
			console.log('Stopped change timer in SuspendTv')
			ebbContainer.suspendPlan()
		}
        onResumeTv: {
			console.log('Started vplan animation.')
			ebbContainer.continuePlan()
		}
		onLoadDesignPictures: {
			ebbHeadImgMiddle.source = headerCenterUrl
			ebbHeadImgLeft.source = headerRptUrl
			ebbHeadImgRight.source = headerRptUrl
		}
		onTimerChange: {
			vplanTimer.interval = vplanInterval
			newsTimer.interval = newsInterval
			annoTimer.interval = annoInterval
		}
		onEbbConfigLoaded: {
			lblRightColumn.text = ebbPlanHandler.rightTitle
			lblLeftColumn.text = ebbPlanHandler.leftTitle
			if (ebbPlanHandler.showTopBoxes) {
				if (ebbHeadBox.state == 'hidden') {
					ebbHeadBox.state = 'visible'
					// Start only, if vplanTimer is also running!
					if (vplanTimer.running) {
						newsTimer.start()
						annoTimer.start()
					}
				}
			} else {
				newsTimer.stop()
				annoTimer.stop()

				if (ebbHeadBox.state != 'hidden') {
					ebbHeadBox.state = 'hidden'
				}
			}
		}
		// Data handlers:
		onNewsAdded: {
            VPlanScripts.createNews(news.id, news.topic, news.subject, news.imgUrl)
		}
		onNewsUpdate: {
			// is the id already in it?
			var foundIdx = -1
			var idx = 0
			var newsTmp = null
			while (idx < newsListModel.count && foundIdx < 0) {
				newsTmp = newsListModel.get(idx)
				if (newsTmp.nid == news.id) {
					foundIdx = idx
					break
				}
				idx += 1
			}
			if (foundIdx >= 0) {
				newsListModel.set(foundIdx, {'nid': news.id, 'subject': news.subject, 'topic': news.topic, 'img': news.imgurl})
			} else {
				newsListModel.append({'nid': news.id, 'subject': news.subject, 'topic': news.topic, 'img': news.imgurl})
			}
		}
		onNewsDeleted: {
			// is the id already in it?
			var foundIdx = -1
			var idx = 0
			var newsTmp = null
			while (idx < newsListModel.count && foundIdx < 0) {
				newsTmp = newsListModel.get(idx)
				if (newsTmp.nid == news.id) {
					foundIdx = idx
					break
				}
				idx += 1
			}

			if (foundIdx >= 0) {
				newsListModel.remove(foundIdx)
				console.log('Removed news index ' + foundIdx + ' with id ' + news.id)
				if (foundIdx == aNewsIdx) {
					nextNews()
				}
			}
		}
		onAnnouncementAdded: {
            VPlanScripts.createAnnouncement(anno.id, anno.section, anno.text, '../../res/img/alert.png')
		}
		onAnnouncementUpdate: {
			// is the id already in it?
			var foundIdx = -1
			var idx = 0
			var annoTmp = null
			while (idx < annoListModel.count && foundIdx < 0) {
				annoTmp = annoListModel.get(idx)
				if (annoTmp.aid == anno.id) {
					foundIdx = idx
					break
				}
				idx += 1
			}
			if (foundIdx >= 0) {
				annoListModel.set(foundIdx, {
					'aid': anno.id, 'title': anno.title, 'section': anno.section, 'text': anno.text,
					'img': '../../res/img/alert.png'
				})
			} else {
				console.log('Didnt found anno. Added it.')
				annoListModel.append({
					'aid': anno.id, 'title': anno.title, 'section': anno.section, 'text': anno.text,
					'img': '../../res/img/alert.png'
				})				
				console.log('Have now: ' + annoListModel.count)
			}
		}
		onAnnouncementDelete: {
			// is the id already in it?
			var foundIdx = -1
			var idx = 0
			var annoTmp = null
			while (idx < annoListModel.count && foundIdx < 0) {
				annoTmp = annoListModel.get(idx)
				if (annoTmp.aid == annoId) {
					foundIdx = idx
					break
				}
				idx += 1
			}

			if (foundIdx >= 0) {
				annoListModel.remove(foundIdx)
				console.log('Removed announcement index ' + foundIdx + ' with id ' + annoId)
				if (foundIdx == aAnnoIdx) {
					nextAnnouncement()
				}
			}
		}
		onPlanAvailable: {
			console.log('Yeah... new plan is available.')
			aDayList = ebbPlanHandler.getTimes
			aPlanList = []
			txtStand.text = qsTr('Stand: ') + ebbPlanHandler.getStand + ' h'
			reloadListModels()
			// restart timer - just to be sure, that he not immediately change
			// the page!
			prepareNextPage()
			if (vplanTimer.running) {
				vplanTimer.stop()
				vplanTimer.start()
			}
		}
		onPlanColSizeChanged: {
			colClass = planSizes.classn
			colHour = planSizes.hour
			colOriginal = planSizes.original
			colChange = planSizes.change
		}
	}

	Timer {
		id: vplanTimer
		interval: 4000
		repeat: true
		running: false
		triggeredOnStart: true
		onTriggered: ebbContainer.nextPage()
	}

	Timer {
		id: newsTimer
		interval: 7000
		repeat: true
        running: false
        triggeredOnStart: false
        onTriggered: {
            if (newsNav.count > 1) {
                if (newsNav.currentIndex < (newsNav.count - 1)) {
                    newsNav.currentIndex += 1
                } else {
                    newsNav.currentIndex = 0
                }
            }
        }
	}

	Timer {
		id: annoTimer
		interval: 4000
		repeat: true
        running: false
        triggeredOnStart: false
        onTriggered: {
            if (newsNav.count > 1) {
                if (newsNav.currentIndex < (newsNav.count - 1)) {
                    newsNav.currentIndex += 1
                } else {
                    newsNav.currentIndex = 0
                }
            }
        }
	}

    Timer {
        id: annoDefaultRemover
        interval: 7500
        repeat: false
        running: false
        onTriggered: {
            announcementView.removeItem(0)
        }
    }

	Item {
		id: ebbHeadContainer
		width: parent.width
		height: 87
		z: 2

		RectangularGlow {
			height: parent.height
			z: 5
			glowRadius: 10
			spread: 0.2
			color: "#000000"
			anchors.topMargin: 20
			anchors.fill: ebbHeadLine
		}

		Rectangle {
			id: ebbHeadLine
			width: parent.width
			height: parent.height
			z: 10

			Image {
				id: ebbHeadImgLeft
				height: ebbHeadImgMiddle.height
				width: ebbHeadImgMiddle.x
				source: "../../res/img/header_wdh.png"
				anchors.right: ebbHeadImgMiddle.left

			}

			Image {
				id: ebbHeadImgMiddle
				source: "../../res/img/header_center.png"
				anchors.centerIn: parent

				Text {
					id: lblLeftColumn
					color: "#ffffff"
					z: 5
					anchors.verticalCenter: parent.verticalCenter
					anchors.left: parent.left
					text: ''
					opacity: 0.85
					textFormat: Text.PlainText
					verticalAlignment: Text.AlignVCenter
					styleColor: "#ffffff"
					font.bold: true
					font.pixelSize: 32
				}

				Text {
					id: lblRightColumn
					color: "#ffffff"
					z: 5
					anchors.verticalCenter: parent.verticalCenter
					anchors.right: parent.right
					text: ''
					anchors.rightMargin: 0
					anchors.verticalCenterOffset: 0
					opacity: 0.85
					textFormat: Text.PlainText
					verticalAlignment: Text.AlignVCenter
					styleColor: "#ffffff"
					font.bold: true
					font.pixelSize: 32
				}
			}

			Image {
				id: ebbHeadImgRight
				height: ebbHeadImgMiddle.height
				width: parent.width - ebbHeadImgMiddle.width - ebbHeadImgLeft.width
				source: "../../res/img/header_wdh.png"
				anchors.left: ebbHeadImgMiddle.right
			}
		}
	}

	Row {
		id: ebbHeadBox
		height: 200
		width: parent.width

		// Announcement box
		Rectangle {
			id: announcementBox
			height: parent.height
			width: (parent.width / 2) - 1
			color: '#ffffff'
			border.color: '#ffffff'
            z: 15

            SwipeView {
                id: announcementView
                height: parent.height - annoNav.height
                width: parent.width
                currentIndex: annoNav.currentIndex
                background: Rectangle {
                    color: "#ffffff"
                }
            }

            // Will be navigation.
            PageIndicator {
                id: annoNav
                height: 20
                interactive: true
                bottomPadding: 2
                rightPadding: 2
                leftPadding: 2
                topPadding: 2
                spacing: 2
                anchors.horizontalCenter: parent.horizontalCenter
                anchors.top: announcementView.bottom
                anchors.topMargin: 0
                currentIndex: announcementView.currentIndex
                count: announcementView.count
            }
		}

		// Border right
		Rectangle {
			width: 1
			height: parent.height
			color: "#D2D2D2"
        }


        // News box
        Rectangle {
            id: newsBox
            height: parent.height
            width: (parent.width / 2) - 1
            color: '#ffffff'
            clip: true
            border.color: '#ffffff'
            z: 15

            SwipeView {
                id: newsView
                height: parent.height - newsNav.height
                width: parent.width
                currentIndex: newsNav.currentIndex
                background: Rectangle {
                    color: "#ffffff"
                }
                Component.onCompleted: newsView.contentItem.highlightMoveDuration = 250
                onCurrentIndexChanged: {
                    if (currentIndex == 0) {
                        state = "atBeginning"
                        newsView.contentItem.highlightMoveDuration = 0
                    } else if (currentIndex >= (count - 1)) {
                        state = "atEnd"
                        newsView.contentItem.highlightMoveDuration = 250
                    } else {
                        state = "inMiddle"
                        newsView.contentItem.highlightMoveDuration = 250
                    }
                }
                states: [
                    State {
                        name: "atBeginning"
                    },
                    State {
                        name: "inMiddle"
                    },
                    State {
                        name: "atEnd"
                    }
                ]
            }

            // Will be navigation.
            PageIndicator {
                id: newsNav
                height: 20
                interactive: true
                bottomPadding: 2
                rightPadding: 2
                leftPadding: 2
                topPadding: 2
                spacing: 2
                anchors.horizontalCenter: parent.horizontalCenter
                anchors.top: newsView.bottom
                anchors.topMargin: 0
                currentIndex: newsView.currentIndex
                count: newsView.count
            }
        }
	}

	Item {
		id: ebbVplanHeadContainer
		width: parent.width
		height: 80

		RectangularGlow {
			anchors.fill: ebbVplanHead.parent
			glowRadius: 8
			spread: 0.1
			color: "#000000"
			cornerRadius: ebbVplanHead.radius + glowRadius
		}

		Rectangle {
			id: ebbVplanHead
			width: parent.width
			height: parent.height
			color: "#DCDCDC"

			Rectangle {
				id: ebbDayBox
				anchors.centerIn: parent
				height: 59
                radius: 10
                color: "#00000000"
                width: 452

				Image {
					source: "../../res/img/vplan_indicator_bg.png"
					anchors.centerIn: parent
					width: parent.width
					height: parent.height

					Image {
						source: "../../res/img/vplan_indicator_glow.png"
					}

					Row {
						width: parent.width
						height: parent.height
						Rectangle {
							id: dayList
							width: 40
							height: parent.height
							color: "#00000000"
							border.color: "#00000000"

							ListModel {
								id: dayListModel
							}
							Component {
								id: dayListDelegate
								Rectangle {
									width: 15
									height: dayListDelegateLabel.height
									color: "#00000000"
									border.color: "#00000000"

									Text {
										id: dayListDelegateLabel
										text: abbr
										font.bold: true
										color: index == dayListView.currentIndex ? '#000000' : '#A3A3A3'
										font.pixelSize: 10
									}
								}
							}
							ListView {
								id: dayListView
								width: parent.width
								height: parent.height

								model: dayListModel
								delegate: dayListDelegate

								anchors.top: parent.top
								anchors.topMargin: 4
								anchors.left: parent.left
								anchors.leftMargin: 8
								anchors.horizontalCenter: parent.horizontalCenter
							}
						}

						Rectangle {
							id: dayName
							width: 330
							height: parent.height
							color: "#00000000"
							border.color: "#00000000"

							Text {
								id: dayNameLabel
								anchors.verticalCenter: parent.verticalCenter
								color: '#000000'
								font.bold: false
								font.pixelSize: 25
								text: ''
							}
						}
						Rectangle {
							id: dayNamePageList
							width: 69
							height: parent.height
							color: "#00000000"
							border.color: "#00000000"

							ListModel {
								id: dayPageListModel
							}
							Component {
								id: dayPageListDelegate
								Rectangle {
									width: 12
									height: 12
									color: "#00000000"
									border.color: "#00000000"

									Image {
										id: dayListDelegateImage
										source: index == dayPageList.currentIndex ? '../../res/img/bullet_selected.png' : '../../res/img/bullet.png'
										anchors.centerIn: parent
									}
								}
							}
							ListView {
								id: dayPageList
								width: parent.width

								model: dayPageListModel
								delegate: dayPageListDelegate
								orientation: ListView.Horizontal

								anchors.top: parent.top
								anchors.topMargin: 23
							}
						}
					}
				}
			}

			Rectangle {
				id: ebbStandCopy
                width: 227
				height: 26
				color: "#00000000"
				border.color: "#00000000"
				anchors.verticalCenterOffset: 0
				anchors.verticalCenter: parent.verticalCenter
				anchors.right: parent.right
				anchors.rightMargin: 30

				Image {
					source: "../../res/img/vplan_stand_bg.png"
					anchors.centerIn: parent
					width: parent.width
					height: parent.height

					Image {
						source: "../../res/img/vplan_stand_glow.png"
					}

					Rectangle {
						id: ebbStand
                        width: 113
						height: parent.height
						color: "transparent"

						Text {
							id: txtStand
							color: "#3E3E3E"
                            text: qsTr("Stand: ") + " "
							horizontalAlignment: Text.AlignHCenter
							verticalAlignment: Text.AlignVCenter
							z: 5
							anchors.fill: parent
							anchors.centerIn: parent
							textFormat: Text.PlainText
							font.bold: true
							font.pixelSize: 8
						}
					}

					Rectangle  {
						id: ebbCopy
						width: parent.width - ebbStand.width
						height: parent.height
						color: "transparent"
						anchors.left: ebbStand.right

						Text {
							id: txtCopy
							color: "#3E3E3E"
							text: "© FLS Wiesbaden"
							verticalAlignment: Text.AlignVCenter
							horizontalAlignment: Text.AlignHCenter
							z: 5
							anchors.fill: parent
							anchors.centerIn: parent
							textFormat: Text.PlainText
							font.bold: true
							font.pixelSize: 8
						}
					}
				}
			}
		}
		Rectangle {
			width: parent.width
			height: 1
			anchors.bottom: ebbVplanHead.bottom
			color: "#989898"
		}
	}

	Component {
		id: vplanComponent

		Item {
			id: vplanItemContainer
			height: gridVplan.cellHeight
			width: (index % 2) ? gridVplan.cellWidth + 2 : gridVplan.cellWidth
			Rectangle {
				color: {
					if (index % 4) {
						if ((index - 1) % 4) {
							"#EAEAEA"
						} else {
							"#D1D1D1"
						}
					} else {
						"#D1D1D1"
					}
				}

				anchors.fill: parent
			}

			Row {
				id: vplanItemContent
				height: 50
				width: vplanItemContainer.width - 10
				anchors.left: parent.left
				anchors.leftMargin: 10
				spacing: 5

				Text {
					text: classn
					height: parent.height
					width: ebbContainer.colClass * parent.width
					font.pixelSize: 19
					color: '#555'
					wrapMode: Text.WordWrap
					verticalAlignment: Text.AlignVCenter
				}
				Text {
					text: hour
					height: parent.height
					width: ebbContainer.colHour * parent.width
					font.pixelSize: 19
					color: '#555'
					wrapMode: Text.WordWrap
					verticalAlignment: Text.AlignVCenter
				}
				Text {
					text: original
					height: parent.height
					width: ebbContainer.colOriginal * parent.width
					font.pixelSize: 19
					color: '#555'
					wrapMode: Text.WordWrap
					verticalAlignment: Text.AlignVCenter
				}
				Text {
					text: change
					height: parent.height
					width: ebbContainer.colChange * parent.width
					font.pixelSize: 19
					color: '#555'
					wrapMode: Text.WordWrap
					verticalAlignment: Text.AlignVCenter
				}
			}

			// Border right
			Rectangle {
				width: 1
				height: parent.height
				anchors.right: vplanItemContent.right
				color: "#B0B0B0"
			}

			// Border bottom
			Rectangle {
				width: parent.width
				height: (classn.length == 0 && hour.length == 0) ? 0 : 1
				anchors.bottom: vplanItemContent.bottom
				color: "#989898"
			}
		}
	}

	Item {
		id: vplanContentContainer
		width: parent.width
		height: Screen.desktopAvailableHeight - vplanContentContainer.y

		// Border bottom
		Rectangle {
			width: parent.width
			height: 1
			anchors.top: vplanContent.top
			color: "#989898"
		}

		Rectangle {
			id: vplanContent
			width: parent.width
			height: parent.height

			ListModel {
				id: vplanModel
			}

			GridView {
				id: gridVplan
				cellWidth: announcementBox.width
				cellHeight: 50
				flow: GridView.FlowLeftToRight
				layoutDirection: Qt.LeftToRight
				verticalLayoutDirection: GridView.TopToBottom
				anchors.fill: parent
				delegate: vplanComponent
				model: vplanModel
				visible: true
				interactive: false

				Behavior on model {
					ParallelAnimation {
						NumberAnimation {
							target: vplanContentSecond
							properties: "x"
							from: 0.0
							to: -parent.width
							duration: 500
						}
						NumberAnimation {
							target: vplanContent
							properties: "x"
							from: parent.width
							to: 0.0
							duration: 500
						}
					}
				}
			}
		}

		Rectangle {
			id: vplanContentSecond
			width: parent.width
			height: parent.height
			x: parent.width + vplanContentSecond.width
			y: vplanContent.y

			ListModel {
				id: vplanModelTemp
			}

			GridView {
				id: gridVplan2
				cellWidth: announcementBox.width
				cellHeight: 50
				flow: GridView.FlowLeftToRight
				layoutDirection: Qt.LeftToRight
				verticalLayoutDirection: GridView.TopToBottom
				anchors.fill: parent
				delegate: vplanComponent
				model: vplanModelTemp
				interactive: false

				Behavior on model {
					ParallelAnimation {
						NumberAnimation {
							target: vplanContent
							properties: "x"
							from: 0.0
							to: -parent.width
							duration: 500
						}
						NumberAnimation {
							target: vplanContentSecond
							properties: "x"
							from: parent.width
							to: 0.0
							duration: 500
						}
					}
				}
			}
		}
	}

	function loadPrimaryData() {
		// Do this here only, if we don't have data yet!
		if (aDayList.length <= 0) {
			aPlanList = []
            txtStand.text = qsTr("Lade Daten...")
			dayNameLabel.text = qsTr("Keine Vertretungen verfügbar.")
			reloadListModels()
			ebbPlanHandler.setMaxEntries(Math.floor(vplanContentContainer.height / (gridVplan.cellHeight + 27))*2)
		}
	}

	function reloadListModels() {
		dayListModel.clear()
		for (var i = 0; i < aDayList.length; i++) {
			dayListModel.append(aDayList[i])
		}
	}

	function nextPage() {
		if (ebbPlanHandler.triggerPresenter && ebbContainer.presenterPageAvailable) {
			ebbContainer.suspendPlan()
			ebbContainer.hookPresenter()
			aDayIdx = -1
		} else {
			// Set the current day index no.
			aDayIdx = ebbPlanHandler.currentDayIndex
			aDayList = ebbPlanHandler.getTimes

			// Switch the plan... Do we have data??
			if (aDayList.length <= 0) {
				aDayIdx = -1
				// Yeah.. here better show a note...
				dayNameLabel.text = qsTr("Keine Vertretungen verfügbar.")
			} else {
				// Change the next page..
				if (otherPageAvailable) {
					if (activModel == 0) {
						gridVplan2.model = vplanModelTemp
						activModel = 1
					} else {
						gridVplan.model = vplanModel
						activModel = 0
					}

					reloadListModels()
					dayPageListModel.clear()
					for (var i = 0; i < aDayList[aDayIdx]['pages']; i++) {
						dayPageListModel.append({'index': i, 'day': aDayList[aDayIdx]['day']})
					}
					
					// Set the current day!
					dayListView.currentIndex = aDayList[aDayIdx]['index']
					dayPageList.currentIndex = ebbPlanHandler.getPageNo
					dayNameLabel.text = aDayList[aDayIdx]['txt']
				}
			}
		}

		prepareNextPage()
		// Next page a presenter, but do we really have it?
		if (ebbPlanHandler.triggerPresenter && !ebbContainer.presenterPageAvailable) {
			prepareNextPage()
		}
	}

	function prepareNextPage() {
		// first calculate the max. number of entries!
		aMaxEntries = Math.round((vplanContentContainer.height / gridVplan.cellHeight)*2)

		// Now prepare the next page.
		aPlanList = ebbPlanHandler.getNextPlan
		if (aPlanList !== false) {
			if (activModel == 0) {
				vplanModelTemp.clear()
			} else {
				vplanModel.clear()
			}
			otherPageAvailable = true
			for (var i = 0; i < aPlanList.length; i++) {
				if (activModel == 0) {
					vplanModelTemp.append(aPlanList[i]);
				} else {
					vplanModel.append(aPlanList[i]);
				}
			}

			aMissingEntries = aMaxEntries - aPlanList.length
			for (var i = 0; i <= aMissingEntries; i++) {
				if (activModel == 0) {
					vplanModelTemp.append({"classn": "", "hour": "", "original": "", "change": ""})
				} else {
					vplanModel.append({"classn": "", "hour": "", "original": "", "change": ""})
				}
			}
		} else {
			otherPageAvailable = false
		}

	}

	function continuePlan() {
		vplanTimer.start()
		if (ebbPlanHandler.showTopBoxes) {
			newsTimer.start()
			annoTimer.start()
		}
	}

	function suspendPlan() {
		vplanTimer.stop()
		newsTimer.stop()
		annoTimer.stop()
	}

	function changePresenterAvailable(pageAvailable) {
		ebbContainer.presenterPageAvailable = pageAvailable
	}
}
