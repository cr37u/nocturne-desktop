pragma Singleton
import QtQuick

// All design tokens in one place (see UI/*.html).
QtObject {
    // Surfaces
    readonly property color bg: "#0A0A14"
    readonly property color panel: "#10101F"
    readonly property color surface: "#141426"
    readonly property color elevated: "#1C1C33"
    readonly property color track: "#2A2A48"
    readonly property color hover: "#16162B"
    readonly property color pillBg: "#161630"

    // Text
    readonly property color text: "#F1F1F7"
    readonly property color textMuted: "#9A9AB8"
    readonly property color textOnGradient: "#D4D4EA"
    readonly property color textSoft: "#C9C9DE"
    readonly property color placeholder: "#8A8AA8"

    // Brand
    readonly property color gradStart: "#1E40AF"
    readonly property color gradEnd: "#3B0764"
    readonly property color gradDeep: "#1A1035"
    readonly property color brightStart: "#3B6CF6"
    readonly property color brightEnd: "#7C3AED"
    readonly property color artStart: "#2B4FD0"
    readonly property color artEnd: "#5B21B6"
    readonly property color amber: "#F5B942"
    readonly property color amberSoft: "#29F5B942"      // 16 %
    readonly property color amberSofter: "#33F5B942"    // 20 %
    readonly property color error: "#F87171"
    readonly property color glow: "#7C3AED"
    readonly property color selection: "#3B6CF6"
    readonly property color onWhite: "#3B0764"
    readonly property color glass: "#1FF1F1F7"          // rgba(241,241,247,0.12)
    readonly property color glassLine: "#24F1F1F7"      // inset 1px 0.14

    // Radii
    readonly property real rPanel: 22
    readonly property real rCard: 24
    readonly property real rInput: 18
    readonly property real rButton: 14

    // Motion
    readonly property int fast: 200
    readonly property int normal: 260

    readonly property string fontFamily: "Manrope"

    // Track / playlist placeholder gradients (from the design rows)
    readonly property var artGradients: [
        ["#1E40AF", "#3B0764"], ["#312E81", "#6D28D9"], ["#1D4ED8", "#4C1D95"], ["#0F172A", "#4338CA"],
        ["#3730A3", "#581C87"], ["#1E3A8A", "#7E22CE"], ["#172554", "#5B21B6"], ["#1E40AF", "#6D28D9"]
    ]
    readonly property var playlistGradients: [
        ["#312E81", "#6D28D9"], ["#1D4ED8", "#4C1D95"], ["#0F172A", "#4338CA"],
        ["#3730A3", "#581C87"], ["#1E3A8A", "#7E22CE"], ["#172554", "#5B21B6"]
    ]

    function icon(name, color) {
        var c = String(color)
        if (c.length === 9) c = "#" + c.substring(3)   // drop alpha: icons are always opaque
        return "image://icon/" + name + "/" + c.replace("#", "")
    }
    function art(seed) { return artGradients[Math.abs(seed || 0) % artGradients.length] }
    function playlistArt(i) { return playlistGradients[Math.abs(i || 0) % playlistGradients.length] }
}
