var newAnno;
var parentAnno;
var defaultAnnoCreated = false;

var newNews;
var parentNews;

function createDefaultAnnouncement() {
    defaultAnnoCreated = true;
    var newAnno = Qt.createComponent("../ui/vplan/announcement.qml");
    parentAnno = newAnno.createObject(announcementView, {
          'aid': '1', 'section': '', 'annoText': 'Willkommen in der Schule!',
          'img': 'https://www.fls-wiesbaden.de/res/ebb/alert.png'
    });
    announcementView.insertItem(0, parentAnno);
}
function createAnnouncement(aid, section, annoText, img) {
    newAnno = Qt.createComponent("../ui/vplan/announcement.qml");
    if (newAnno.status === Component.Error) {
        console.error("Error creating announcement component: ", newAnno.errorString());
    } else {
        parentAnno = newAnno.createObject(announcementView, {
              'aid': aid, 'section': section, 'annoText': annoText,
              'img': img
        });
        if (defaultAnnoCreated) {
            annoDefaultRemover.start()
            defaultAnnoCreated = false;
        }
        announcementView.addItem(parentAnno);
    }
}

function clearAnnouncements() {
    for(var i = 0; i < announcementView.count; i++) {
        announcementView.removeItem(i);
    }
    createDefaultAnnouncement();
}

function createNews(nid, section, newsText, img) {
    newNews = Qt.createComponent("../ui/vplan/news.qml");
    if (newNews.status === Component.Error) {
        console.error("Error creating news component: ", newNews.errorString());
    } else {
        parentNews = newNews.createObject(newsView, {
              'nid': nid, 'section': section, 'newsText': newsText,
              'img': img
        });
        newsView.addItem(parentNews);
    }
}

function clearNews() {
    for(var i = 0; i < newsView.count; i++) {
        newsView.removeItem(i);
    }
}

function vplanConnected() {
    ebbDayBox.border.color = "#00000000";
    ebbDayBox.border.width = 1;
}

function vplanDisconnected() {
    ebbDayBox.border.width = 10;
    ebbDayBox.border.color = "#cf0707";
}
