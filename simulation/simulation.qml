import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ApplicationWindow {
    id: window
    width: 1420
    height: 900
    visible: true
    title: "AGV Route Simulation"
    color: "#0B1020"

    property var mapState: ({ matrix: [], starts: [], goals: [] })
    property var selectedNodes: []
    property var routeResult: ({ ok: false, segments: [], path: [] })
    property var routeLookup: ({})

    function loadMap() {
        mapState = JSON.parse(simulationController.mapData)
        selectedNodes = []
        routeResult = ({ ok: false, segments: [], path: [] })
        routeLookup = ({})
        mapCanvas.requestPaint()
    }

    function toggleRoom(nodeIndex) {
        let updated = selectedNodes.slice()
        let position = updated.indexOf(nodeIndex)
        if (position >= 0)
            updated.splice(position, 1)
        else
            updated.push(nodeIndex)
        selectedNodes = updated
        calculateRoute()
    }

    function calculateRoute() {
        if (selectedNodes.length === 0) {
            routeResult = ({ ok: false, segments: [], path: [] })
            routeLookup = ({})
            mapCanvas.requestPaint()
            return
        }

        routeResult = JSON.parse(simulationController.calculate_route(selectedNodes))
        let lookup = {}
        if (routeResult.ok) {
            routeResult.path.forEach((cell, index) => {
                lookup[cell[0] + "_" + cell[1]] = index
            })
        }
        routeLookup = lookup
        mapCanvas.requestPaint()
    }

    Component.onCompleted: loadMap()

    Connections {
        target: simulationController
        function onMapChanged() {
            window.loadMap()
        }
    }

    header: Rectangle {
        height: 76
        color: "#111A2E"
        border.color: "#243451"

        RowLayout {
            anchors.fill: parent
            anchors.leftMargin: 26
            anchors.rightMargin: 26

            ColumnLayout {
                spacing: 2
                Text {
                    text: "AGV Route Simulation"
                    color: "white"
                    font.pixelSize: 25
                    font.bold: true
                }
                Text {
                    text: "Uses the same map data as the main UI. No hardware is accessed."
                    color: "#8FA4C7"
                    font.pixelSize: 13
                }
            }

            Item { Layout.fillWidth: true }

            Button {
                text: "Reload map"
                onClicked: simulationController.reload_map()
            }

            Button {
                text: "Clear"
                onClicked: {
                    selectedNodes = []
                    calculateRoute()
                }
            }
        }
    }

    RowLayout {
        anchors.fill: parent
        anchors.margins: 18
        spacing: 18

        Rectangle {
            Layout.fillWidth: true
            Layout.fillHeight: true
            Layout.preferredWidth: 900
            color: "#111827"
            radius: 14
            border.color: "#26344E"

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 16
                spacing: 12

                RowLayout {
                    Layout.fillWidth: true
                    Text {
                        text: "Shared map"
                        color: "white"
                        font.pixelSize: 20
                        font.bold: true
                    }
                    Item { Layout.fillWidth: true }
                    Text {
                        text: routeResult.ok ? routeResult.totalSteps + " grid steps" : "Select rooms"
                        color: "#67E8F9"
                        font.pixelSize: 15
                        font.bold: true
                    }
                }

                Item {
                    id: mapArea
                    Layout.fillWidth: true
                    Layout.fillHeight: true

                    Canvas {
                        id: mapCanvas
                        anchors.centerIn: parent
                        width: {
                            let columns = mapState.matrix.length > 0 ? mapState.matrix[0].length : 1
                            let rows = mapState.matrix.length > 0 ? mapState.matrix.length : 1
                            return Math.min(parent.width, parent.height * columns / rows)
                        }
                        height: {
                            let columns = mapState.matrix.length > 0 ? mapState.matrix[0].length : 1
                            let rows = mapState.matrix.length > 0 ? mapState.matrix.length : 1
                            return width * rows / columns
                        }

                        onPaint: {
                            let context = getContext("2d")
                            context.reset()
                            if (!mapState.matrix || mapState.matrix.length === 0)
                                return

                            let rows = mapState.matrix.length
                            let columns = mapState.matrix[0].length
                            let cellWidth = width / columns
                            let cellHeight = height / rows
                            let goalLabels = {}
                            mapState.goals.forEach(goal => {
                                goalLabels[goal[0] + "_" + goal[1]] = String(goal[2])
                            })

                            for (let row = 0; row < rows; row++) {
                                for (let column = 0; column < columns; column++) {
                                    let value = mapState.matrix[row][column]
                                    let key = row + "_" + column
                                    let fill = value === 1 ? "#20293A" : "#D7E3F4"
                                    if (routeLookup[key] !== undefined)
                                        fill = "#2DD4BF"
                                    if (value === 3)
                                        fill = "#F59E0B"
                                    if (value === 2)
                                        fill = selectedNodes.includes(
                                            mapState.goals.findIndex(
                                                goal => goal[0] === row && goal[1] === column
                                            ) + 1
                                        ) ? "#F43F5E" : "#3B82F6"

                                    context.fillStyle = fill
                                    context.fillRect(
                                        column * cellWidth,
                                        row * cellHeight,
                                        cellWidth,
                                        cellHeight
                                    )
                                    context.strokeStyle = "#0F172A"
                                    context.lineWidth = 0.55
                                    context.strokeRect(
                                        column * cellWidth,
                                        row * cellHeight,
                                        cellWidth,
                                        cellHeight
                                    )

                                    if (value === 2 || value === 3) {
                                        context.fillStyle = "white"
                                        context.font = Math.max(9, cellWidth * 0.42) + "px sans-serif"
                                        context.textAlign = "center"
                                        context.textBaseline = "middle"
                                        context.fillText(
                                            value === 3 ? "K" : goalLabels[key],
                                            (column + 0.5) * cellWidth,
                                            (row + 0.5) * cellHeight
                                        )
                                    }
                                }
                            }

                            if (routeResult.ok && routeResult.path.length > 1) {
                                context.strokeStyle = "#F8FAFC"
                                context.lineWidth = Math.max(2, cellWidth * 0.14)
                                context.lineCap = "round"
                                context.lineJoin = "round"
                                context.beginPath()
                                routeResult.path.forEach((cell, index) => {
                                    let x = (cell[1] + 0.5) * cellWidth
                                    let y = (cell[0] + 0.5) * cellHeight
                                    if (index === 0)
                                        context.moveTo(x, y)
                                    else
                                        context.lineTo(x, y)
                                })
                                context.stroke()
                            }
                        }
                    }
                }

                RowLayout {
                    spacing: 18
                    Repeater {
                        model: [
                            ["#F59E0B", "Kitchen"],
                            ["#3B82F6", "Room"],
                            ["#F43F5E", "Selected"],
                            ["#2DD4BF", "Optimal path"]
                        ]
                        delegate: RowLayout {
                            spacing: 6
                            Rectangle {
                                width: 14
                                height: 14
                                radius: 3
                                color: modelData[0]
                            }
                            Text {
                                text: modelData[1]
                                color: "#B8C5DA"
                            }
                        }
                    }
                }
            }
        }

        Rectangle {
            Layout.preferredWidth: 440
            Layout.fillHeight: true
            color: "#111827"
            radius: 14
            border.color: "#26344E"

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 16
                spacing: 12

                Text {
                    text: "Select delivery rooms"
                    color: "white"
                    font.pixelSize: 20
                    font.bold: true
                }

                GridLayout {
                    Layout.fillWidth: true
                    columns: 2
                    columnSpacing: 10
                    rowSpacing: 10

                    Repeater {
                        model: mapState.goals || []
                        delegate: Button {
                            required property var modelData
                            required property int index
                            Layout.fillWidth: true
                            Layout.preferredHeight: 58
                            text: "Room " + modelData[2]
                            checkable: true
                            checked: selectedNodes.includes(index + 1)
                            onClicked: toggleRoom(index + 1)
                        }
                    }
                }

                Rectangle {
                    Layout.fillWidth: true
                    height: 72
                    radius: 10
                    color: "#172238"
                    border.color: "#2D4265"

                    Column {
                        anchors.fill: parent
                        anchors.margins: 12
                        spacing: 5
                        Text {
                            text: routeResult.ok
                                ? routeResult.routeLabels.join("  >  ")
                                : "Choose one or more rooms"
                            width: parent.width
                            color: routeResult.ok ? "#67E8F9" : "#94A3B8"
                            font.pixelSize: 15
                            font.bold: routeResult.ok
                            wrapMode: Text.Wrap
                        }
                        Text {
                            text: routeResult.ok
                                ? "The route returns to the kitchen automatically."
                                : "The simulator recalculates after every click."
                            color: "#8799B8"
                            font.pixelSize: 12
                        }
                    }
                }

                Text {
                    text: "Route instructions"
                    color: "white"
                    font.pixelSize: 18
                    font.bold: true
                }

                ScrollView {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    clip: true

                    ListView {
                        spacing: 10
                        model: routeResult.ok ? routeResult.segments : []

                        delegate: Rectangle {
                            required property var modelData
                            width: ListView.view.width
                            height: instructionColumn.implicitHeight + 24
                            radius: 10
                            color: "#172238"
                            border.color: "#2D4265"

                            Column {
                                id: instructionColumn
                                anchors.left: parent.left
                                anchors.right: parent.right
                                anchors.top: parent.top
                                anchors.margins: 12
                                spacing: 5

                                Text {
                                    text: (index + 1) + ". " + modelData.from + "  >  " + modelData.to
                                    color: "white"
                                    font.pixelSize: 15
                                    font.bold: true
                                }
                                Text {
                                    text: modelData.steps + " steps, "
                                        + modelData.intersections + " intersections"
                                    color: "#A9B8D0"
                                    font.pixelSize: 13
                                }
                                Text {
                                    width: parent.width
                                    text: modelData.turns.length > 0
                                        ? modelData.turns.map(turn =>
                                            "Intersection " + turn.intersection + ": " + turn.label
                                          ).join("  |  ")
                                        : "Continue straight; no turn instruction."
                                    color: "#67E8F9"
                                    font.pixelSize: 13
                                    wrapMode: Text.Wrap
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}
