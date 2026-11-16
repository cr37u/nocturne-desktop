import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts

ColumnLayout {
    id: root
    spacing: 20
    function focusLink() { linkField.focusField() }

    readonly property var detected: Downloads.detected
    readonly property bool hasDetected: detected && detected.title !== undefined

    // Header
    RowLayout {
        Layout.fillWidth: true
        spacing: 16
        ColumnLayout {
            Layout.fillWidth: true
            spacing: 4
            Text {
                Layout.fillWidth: true
                text: qsTr("Downloads")
                color: Theme.text
                font.pixelSize: 34
                font.weight: Font.ExtraBold
                font.letterSpacing: -0.7
                elide: Text.ElideRight
            }
            Text {
                Layout.fillWidth: true
                text: Downloads.totalCount === 0 ? qsTr("Paste a link to download a song or a whole playlist.")
                    : (Fmt.revision >= 0 ? qsTr("%1 of %2").arg(Fmt.number(Downloads.completedCount)).arg(Fmt.number(Downloads.totalCount)) : "")
                      + (Downloads.speed > 0 ? " · " + Fmt.speed(Downloads.speed) : "")
                color: Theme.textMuted
                font.pixelSize: 14
                elide: Text.ElideRight
            }
        }
        RowLayout {
            Layout.alignment: Qt.AlignBottom
            spacing: 10
            NButton {
                visible: Downloads.model.count > 0
                text: qsTr("Clear finished")
                bg: Theme.surface
                textColor: Theme.textMuted
                fontSize: 13
                onClicked: Downloads.clearFinished()
            }
            NButton {
                visible: Downloads.pendingCount > 0
                text: Downloads.paused ? qsTr("Resume all") : qsTr("Pause all")
                icon: Downloads.paused ? "play" : "pause"
                iconSize: 15
                iconColor: Theme.amber
                bg: Theme.surface
                onClicked: Downloads.paused ? Downloads.resumeAll() : Downloads.pauseAll()
            }
        }
    }

    LinkField {
        id: linkField
        Layout.fillWidth: true
        buttonText: qsTr("Check link")
        buttonIcon: "search"
        onSubmitted: (t) => Downloads.analyze(t)
    }

    // Detected card
    Rectangle {
        Layout.fillWidth: true
        visible: root.hasDetected
        implicitHeight: detCol.implicitHeight + 40
        radius: Theme.rCard
        color: Theme.surface
        border.width: 1
        border.color: "#33F5B942"
        opacity: visible ? 1 : 0
        Behavior on opacity { NumberAnimation { duration: Theme.normal } }

        RowLayout {
            id: detCol
            anchors.fill: parent
            anchors.margins: 20
            spacing: 18
            GradientRect {
                Layout.preferredWidth: 72
                Layout.preferredHeight: 72
                radius: 18
                Icon {
                    anchors.centerIn: parent
                    name: root.hasDetected && root.detected.kind === "playlist" ? "playlists" : "music"
                    size: 30
                }
            }
            ColumnLayout {
                Layout.fillWidth: true
                spacing: 4
                Text {
                    text: root.hasDetected && root.detected.kind === "playlist" ? qsTr("PLAYLIST DETECTED") : qsTr("VIDEO DETECTED")
                    color: Theme.amber
                    font.pixelSize: 11
                    font.weight: Font.ExtraBold
                    font.letterSpacing: 1.3
                }
                Text {
                    Layout.fillWidth: true
                    text: root.hasDetected ? root.detected.title : ""
                    color: Theme.text
                    font.pixelSize: 18
                    font.weight: Font.ExtraBold
                    elide: Text.ElideRight
                }
                Text {
                    Layout.fillWidth: true
                    text: !root.hasDetected ? "" :
                          (Fmt.revision >= 0 ? Fmt.songs(root.detected.count) : "") + " · " + Fmt.totalDuration(root.detected.duration)
                          + (root.detected.existing > 0 ? " · " + qsTr("%n already in library", "", root.detected.existing) : "")
                    color: Theme.textMuted
                    font.pixelSize: 13
                    elide: Text.ElideRight
                }
                RowLayout {
                    Layout.fillWidth: true
                    Layout.topMargin: 8
                    spacing: 10
                    NButton {
                        gradient: true
                        icon: "download"
                        enabled: root.hasDetected && root.detected.newCount > 0
                        text: !root.hasDetected ? "" : root.detected.newCount > 0
                              ? qsTr("Download %n new song(s)", "", root.detected.newCount)
                              : qsTr("Already downloaded")
                        onClicked: Downloads.downloadDetected()
                    }
                    NButton {
                        text: qsTr("Cancel")
                        bg: Theme.elevated
                        textColor: Theme.textMuted
                        fontSize: 13
                        onClicked: Downloads.dismissDetected()
                    }
                    Item { Layout.fillWidth: true }
                }
            }
        }
    }

    // List
    Rectangle {
        Layout.fillWidth: true
        Layout.fillHeight: true
        color: Theme.panel
        radius: Theme.rPanel

        ColumnLayout {
            anchors.fill: parent
            anchors.margins: 16
            spacing: 12
            visible: Downloads.model.count > 0
            SeekBar {
                Layout.fillWidth: true
                barHeight: 5
                value: Downloads.progress
                interactive: false
                showThumb: false
                trackColor: Theme.elevated
                visible: Downloads.totalCount > 0
            }
            ListView {
                id: dlList
                Layout.fillWidth: true
                Layout.fillHeight: true
                clip: true
                spacing: 4
                model: Downloads.model
                boundsBehavior: Flickable.StopAtBounds
                ScrollBar.vertical: NScrollBar {}
                delegate: Rectangle {
                    id: dl
                    required property string key
                    required property string videoId
                    required property string title
                    required property string artist
                    required property string state
                    required property real progress
                    required property real downloaded
                    required property real total
                    required property real speed
                    required property string error
                    required property int attempt
                    width: dlList.width - 8
                    height: 64
                    radius: 14
                    color: dlHover.hovered ? Theme.surface : "transparent"
                    HoverHandler { id: dlHover }

                    RowLayout {
                        anchors.fill: parent
                        anchors.leftMargin: 12
                        anchors.rightMargin: 12
                        spacing: 14
                        Artwork {
                            Layout.preferredWidth: 40
                            Layout.preferredHeight: 40
                            radius: 11
                            source: "https://i.ytimg.com/vi/" + dl.videoId + "/mqdefault.jpg"
                            seed: dl.videoId.length
                            iconSize: 16
                        }
                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 4
                            Text {
                                Layout.fillWidth: true
                                text: dl.title
                                color: Theme.text
                                font.pixelSize: 14
                                font.weight: Font.Bold
                                elide: Text.ElideRight
                            }
                            Text {
                                Layout.fillWidth: true
                                visible: dl.state !== "active"
                                text: dl.state === "failed" ? dl.error
                                    : dl.state === "active" ? "" : dl.artist
                                color: dl.state === "failed" ? Theme.error : Theme.textMuted
                                font.pixelSize: 12
                                elide: Text.ElideRight
                            }
                            RowLayout {
                                visible: dl.state === "active"
                                Layout.fillWidth: true
                                spacing: 10
                                SeekBar {
                                    Layout.fillWidth: true
                                    barHeight: 4
                                    value: dl.progress
                                    interactive: false
                                    showThumb: false
                                    trackColor: Theme.elevated
                                }
                                Text {
                                    text: dl.total > 0
                                          ? qsTr("%1 / %2").arg(Fmt.size(dl.downloaded)).arg(Fmt.size(dl.total))
                                            + (dl.speed > 0 ? " · " + Fmt.speed(dl.speed) : "")
                                          : qsTr("Connecting…")
                                    color: Theme.textMuted
                                    font.pixelSize: 12
                                }
                            }
                        }
                        // State column
                        RowLayout {
                            spacing: 8
                            Text {
                                visible: dl.state === "active"
                                text: Fmt.percent(dl.progress)
                                color: Theme.text
                                font.pixelSize: 13
                                font.weight: Font.Bold
                            }
                            Icon {
                                visible: dl.state === "done" || dl.state === "skipped"
                                name: "check"; size: 16; color: Theme.amber
                            }
                            Text {
                                visible: dl.state !== "active"
                                text: dl.state === "done" || dl.state === "skipped" ? qsTr("Done")
                                    : dl.state === "failed" ? qsTr("Failed")
                                    : dl.state === "paused" ? qsTr("Paused")
                                    : qsTr("Waiting")
                                color: dl.state === "done" || dl.state === "skipped" ? Theme.amber
                                     : dl.state === "failed" ? Theme.error : Theme.textMuted
                                font.pixelSize: 13
                                font.weight: Font.Bold
                            }
                            NButton {
                                visible: dl.state === "failed"
                                implicitHeight: 32
                                padH: 12
                                radius: 10
                                bg: Theme.elevated
                                icon: "retry"
                                iconSize: 14
                                text: qsTr("Retry")
                                fontSize: 12
                                onClicked: Downloads.retry(dl.key)
                            }
                            NButton {
                                visible: dl.state !== "done" && dl.state !== "skipped"
                                implicitWidth: 32; implicitHeight: 32; radius: 10
                                icon: "close"; iconSize: 14; iconColor: Theme.textMuted
                                tooltip: qsTr("Remove")
                                onClicked: Downloads.cancel(dl.key)
                            }
                        }
                    }
                }
            }
        }

        ColumnLayout {
            anchors.centerIn: parent
            visible: Downloads.model.count === 0
            width: Math.min(420, parent.width - 40)
            spacing: 12
            Icon { Layout.alignment: Qt.AlignHCenter; name: "download"; size: 40; color: Theme.textMuted }
            Text {
                Layout.fillWidth: true
                horizontalAlignment: Text.AlignHCenter
                wrapMode: Text.Wrap
                text: qsTr("No downloads yet. Videos, Shorts, YouTube Music links and whole playlists are supported.")
                color: Theme.textMuted
                font.pixelSize: 14
            }
        }
    }
}
