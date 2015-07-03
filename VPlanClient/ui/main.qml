import QtQuick 2.4
import QtGraphicalEffects 1.0
import QtQuick.Controls 1.3
import QtQuick.Window 2.2
import EbbContentHandler 1.0
import "pages"

StackView {
	id: stackView
	property bool browser: true
	property VplanPage pWeb: null
	property PresenterPage pPdf: null
	property ContentPage pContent: null
	property FirealarmPage pFirealarm: null
	property bool contentReady: false
	property var currentMode: 'default'

	signal continuePlan()
	signal stopPlan()
	signal presentPageAvailable(bool pageAvailable)

	EbbContentHandler {
		id: ebbContentHandler
		objectName: "ebbContentHandler"

		onContentDeassigned: {
			stackView.contentReady = false
			presenterPdfModel.clear()
			stackView.presentPageAvailable(false)
		}

		onContentAssigned: {
			stackView.contentReady = true
			stackView.presentPageAvailable(true)
		}

		onPageAdded: {
			presenterPdfModel.append({imagePath: pdfPagePath})
		}

		onModeChanged: {
			var previousMode = currentMode
			if (toMode != 'default') {
				// Stop the eBB
				stackView.stopPlan()
			}
			if (toMode != currentMode) {
				stackView.pop()
				currentMode = toMode
			}
			if (toMode == 'content') {
				if (presenterPdfModel.count > 0) {
					currentMode = 'presenter'
					pPdf = stackView.push(Qt.resolvedUrl("pages/PresenterPage.qml"))
					pPdf.setBasicData(presenterPdfModel, ebbContentHandler.cycleTime)
					pPdf.setLoop(true)
				} else {
					pContent = stackView.push(Qt.resolvedUrl('pages/ContentPage.qml'))
					pContent.updateArrow(ebbContentHandler.contentArrowDirection)
					pContent.updateContent(ebbContentHandler.contentArrow, ebbContentHandler.contentText)
				}
			} else if (toMode == 'firealarm') {
				pFirealarm = stackView.push(Qt.resolvedUrl('pages/FirealarmPage.qml'))
				pFirealarm.updateArrow(ebbContentHandler.fireArrow)
			} else if (toMode == 'default') {
				if (previousMode == 'default') {
					// Nothing todo....
				} else {
					stackView.continuePlan()
				}
			}
		}

		onContentArrowChanged: {
			if (currentMode == 'content') {
				pContent.updateArrow(newDirection)
			}
		}

		onContentBodyChanged: {
			if (currentMode == 'content') {
				pContent.updateContent(ebbContentHandler.contentArrow, ebbContentHandler.contentText)
			}
		}

		onFireArrowChanged: {
			if (currentMode == 'firealarm') {
				pFirealarm.updateArrow(newDirection)
			}
		}
	}

	ListModel {
		id: presenterPdfModel
	}

	Component.onCompleted: {
		pWeb = stackView.push(Qt.resolvedUrl("pages/VplanPage.qml"))
		pWeb.onHookPresenter.connect(startPresenter)
		stackView.continuePlan.connect(pWeb.continuePlan)
		stackView.stopPlan.connect(pWeb.suspendPlan)
		stackView.presentPageAvailable.connect(pWeb.changePresenterAvailable)
	}

	function startPresenter() {
		if (stackView.contentReady) {
			pPdf = stackView.push(Qt.resolvedUrl("pages/PresenterPage.qml"))
			pPdf.onFinished.connect(presenterFinished)
			pPdf.setBasicData(presenterPdfModel, ebbContentHandler.cycleTime)
		} else {
			if (currentMode == 'default') {
				stackView.continuePlan()
			}
		}
	}

	function presenterFinished() {
		stackView.pop()
		if (currentMode == 'default') {
			stackView.continuePlan()
		}
	}

	delegate: StackViewDelegate {
		function transitionFinished(properties)
		{
			properties.exitItem.x = 0
		}

		pushTransition: StackViewTransition {
			SequentialAnimation {
				PropertyAnimation {
					target: enterItem
					property: "x"
					from: enterItem.width
					to: 0
					duration: 500
				}
			}
			PropertyAnimation {
				target: exitItem
				property: "x"
				from: 0
				to: -exitItem.width
				duration: 500
			}
		}
	}
}
