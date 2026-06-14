import QtQuick
import QtQuick.Layouts
import QtQuick.Controls

Window {
    id: app
    width: 1300
    height: 900
    visible: true
    title: qsTr("Responsive App in QML")

    visibility: Window.Maximized

    property bool isMobileView: width <= 450
    property bool isTabletView: !isMobileView && width <= 750
    property bool isDesktopView: !isMobileView && !isTabletView
    property real selectedMenuIndex: 0
    property bool sidebarExpanded: true

    property int mapColCount: 30
    property int mapRowCount: 30

    signal mapRoomsChanged()

    function applyMapState(mapData) {
        if (mapData === "") {
            mapSharedModel.clear()
            roomListModel.clear()
            for (let i = 0; i < mapColCount * mapRowCount; i++) {
                mapSharedModel.append({ cellType: 1, destNumber: "" })
            }
            mapRoomsChanged()
            return
        }

        let state = typeof mapData === "string" ? JSON.parse(mapData) : mapData
        let mapMatrix = state.matrix
        let savedGoals = state.goals || []
        let goalDict = {}

        savedGoals.forEach(g => { goalDict[g[0] + "_" + g[1]] = g[2] })

        app.mapRowCount = mapMatrix.length
        app.mapColCount = mapMatrix[0].length
        mapSharedModel.clear()
        roomListModel.clear()

        savedGoals.forEach((goal, goalIndex) => {
            roomListModel.append({
                roomLabel: String(goal[2]),
                nodeIndex: goalIndex + 1
            })
        })

        for (let r = 0; r < app.mapRowCount; r++) {
            for (let c = 0; c < app.mapColCount; c++) {
                let cellType = mapMatrix[r][c]
                let destinationNumber =
                    cellType === 2 && goalDict[r + "_" + c] ? goalDict[r + "_" + c] : ""
                mapSharedModel.append({
                    cellType: cellType,
                    destNumber: destinationNumber
                })
            }
        }
        mapRoomsChanged()
    }

    function refreshMapHistory() {
        mapHistoryModel.clear()
        let historyData = robotController.list_map_history()
        if (historyData === "")
            return

        let history = JSON.parse(historyData)
        history.forEach(item => {
            mapHistoryModel.append({
                snapshotId: item.id,
                createdAt: item.created_at,
                historyLabel: item.label,
                rowCount: item.rows,
                columnCount: item.columns,
                startCount: item.start_count,
                goalCount: item.goal_count
            })
        })
    }

    ListModel {
        id: mapSharedModel

        Component.onCompleted: {
            app.applyMapState(robotController.load_map_data())
        }
    }

    ListModel {
        id: roomListModel
    }

    ListModel {
        id: mapHistoryModel
    }

    Connections {
        target: robotController  // Listen for the signal from this object

        // Đã sửa lại cú pháp chuẩn của Connections trên Qt6
        function onRobotStopped(status) {
            if (status === "SUCCESS") {
                console.log("Robot has stopped!");
                stackView.pop()
            } else if (status === "RETURNN") {
                console.log("Rbot returning")
                stackView.push(page3)
            } else if (status === "RETURNING"){
                stackView.clear()
                stackView.push(mainPage)
            } else if (status === "STOPTEST"){
                stackView.clear()
                stackView.push(mainPage)
            }
        }
    }

    StackView{
        id: stackView
        anchors.fill: parent
        initialItem: mainPage
    }

    Component{
        id: mainPage
        Item{
            // Desktop Layout
            RowLayout {
                anchors.fill: parent
                spacing: 0
                visible: isDesktopView
                LayoutItemProxy {
                    id: sidebarProxy
                    target: expandedSidebar
                    Layout.preferredWidth: expandedSidebar.sidebarWidth  // Bind to sidebar width
                    Layout.fillHeight: true
                }

                ColumnLayout {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    spacing: 0  // Ensure no extra spacing
                    LayoutItemProxy {
                        target: topNavbar
                        height: 100
                        Layout.fillWidth: true
                    }

                    LayoutItemProxy {
                        target: mainContent
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                    }
                }
            }

            // Tablet Layout
            RowLayout {
                anchors.fill: parent
                spacing: 0
                visible: isTabletView

                LayoutItemProxy {
                    target: expandedSidebar
                    width: 70 // Minimize the side bar
                    Layout.fillHeight: true
                }

                ColumnLayout {
                    Layout.fillWidth: true
                    Layout.fillHeight: true

                    LayoutItemProxy {
                        target: topNavbar
                        height: 60
                        Layout.fillWidth: true
                    }

                    LayoutItemProxy {
                        target: mainContent
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                    }
                }
            }

            // Mobile Layout
            ColumnLayout {
                anchors.fill: parent
                visible: isMobileView

                LayoutItemProxy {
                    target: topNavbar
                    height: 60
                    Layout.fillWidth: true
                }

                LayoutItemProxy {
                    target: mainContent
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                }
            }


            // ------ RE USABLE COMPONENTS ----- //
            // --------------------------------- //

            Drawer {
                id: drawer
                edge: Qt.LeftEdge
                width: 300
                height: app.height
                interactive: isMobileView
                modal: true

                background: Rectangle {
                    color: "#a4b0be"
                }

                contentItem: LayoutItemProxy {
                    target: expandedSidebar
                    width: 500
                    height: drawer.height
                }
            }

            // Application top bar
            Rectangle {
                id: expandedSidebar
                property int sidebarWidth: 0  // Start with width 70
                color: "#2C3A47"
                clip: true

                Column {
                    anchors.fill: parent

                    Item {
                        height: 80
                        width: parent.width


                        Rectangle {
                            width: 40
                            height: 80
                            radius: 8
                            anchors.centerIn: parent
                        }
                        MouseArea {
                            anchors.fill: parent
                            onClicked: {
                                expandedSidebar.sidebarWidth = (expandedSidebar.sidebarWidth === 200) ? 70 : 200;
                            }
                        }
                    }

                    Repeater {
                        width: parent.width
                        model: 0

                        delegate: Item {
                            width: parent.width
                            height: menurow.height

                            Row {
                                id: menurow
                                spacing: 0

                                Item {
                                    width: 70
                                    height: 50

                                    Rectangle {
                                        width: 10
                                        height: parent.height
                                        radius: width/2
                                        anchors.left: parent.left
                                        anchors.leftMargin: -radius
                                        color: "orange"
                                        visible: selectedMenuIndex===index
                                    }

                                    Rectangle {
                                        width: 40
                                        height: 40
                                        radius: 8
                                        anchors.centerIn: parent
                                    }
                                }

                                Text {
                                    anchors.verticalCenter: parent.verticalCenter
                                    text: qsTr("Menu ") + (index+1).toString()
                                    font.pixelSize: 14
                                    color: "#444"
                                }
                            }

                            MouseArea {
                                anchors.fill: parent
                                onClicked: selectedMenuIndex=index
                            }
                        }
                    }
                }
            }
            // Application top bar
            Rectangle {
                id: topNavbar
                color: "#1B2236"
                height: 60
                width: parent.width

                Row {
                    anchors.fill: parent  // Ensure the row fills the parent
                    anchors.centerIn: parent  // Center the row vertically within the Rectangle
                    spacing: 5  // Add some space between the image and text

                    Image {
                        anchors.verticalCenter: parent.verticalCenter
                        id: myImage
                        source: "qrc:/ilg/Image/logo-hust.png"
                        width: 100
                        height: 100
                        fillMode: Image.PreserveAspectFit
                    }

                    Text {
                        id: hell
                        text: qsTr("Ha Noi University of Science and Technology\nResearch Center for Propulsion Systems and Autonomous Vehicles")
                        color: "White"
                        font.pixelSize: 25
                        font.bold: true
                        anchors.verticalCenter: parent.verticalCenter  // Vertically center the text in the row
                    }
                }


                /*===========================================================================*/
                Rectangle {
                    width: 40; height: 40
                    color: "#3B82F6"
                    radius: 8
                    anchors.right: parent.right
                    anchors.verticalCenter: parent.verticalCenter
                    anchors.rightMargin: 20

                    Text { text: "🗺️"; anchors.centerIn: parent; font.pixelSize: 20 }

                    MouseArea {
                        anchors.fill: parent
                        cursorShape: Qt.PointingHandCursor
                        onClicked: {
                            stackView.push(mapPage) // Mở trang Map
                        }
                    }
                }
                /*===========================================================================*/
            }

            Rectangle {
                id: mainContent
                color: "Black"
                readonly property real minCellWidth: 200
                property var selectedButtonIndices: [] // Store selected indices

                Connections {
                    target: app
                    function onMapRoomsChanged() {
                        mainContent.selectedButtonIndices = []
                    }
                }

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 10

                    GridView {
                        id: gridView
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        model: roomListModel
                        clip: true
                        cellWidth: width  / 4
                        cellHeight: cellWidth * 0.55

                        delegate: Item {
                            width: gridView.cellWidth
                            height: gridView.cellHeight

                            Button {
                                id: tableButton
                                anchors.fill: parent
                                anchors.margins: 12 // Tăng margin một chút để các thẻ cách nhau thoáng hơn
                                hoverEnabled: true // Bật hover để lát làm hiệu ứng

                                // 1. Tùy chỉnh Nền (Background) của thẻ
                                background: Rectangle {
                                    id: buttonBg
                                    radius: 8
                                    // Màu nền: Nếu được chọn thì xanh sáng hơn chút, bình thường thì xanh đen
                                    color: mainContent.selectedButtonIndices.includes(model.nodeIndex) ? "#27314A" : "#1B2236"

                                    // Viền: Nếu được chọn thì hiện viền xanh dương (giống R101 trong mẫu)
                                    border.color: mainContent.selectedButtonIndices.includes(model.nodeIndex) ? "#3B82F6" : "transparent"
                                    border.width: mainContent.selectedButtonIndices.includes(model.nodeIndex) ? 2 : 0

                                    // Hiệu ứng hover cho mượt
                                    Rectangle {
                                        anchors.fill: parent
                                        radius: 8
                                        color: "white"
                                        opacity: tableButton.hovered && !mainContent.selectedButtonIndices.includes(model.nodeIndex) ? 0.05 : 0
                                    }
                                }

                                // 2. Tùy chỉnh Nội dung (Content) bên trong thẻ
                                contentItem: Item {
                                    // Dùng một Item vô hình bọc ngoài cùng để bắt nó phủ kín Button
                                    anchors.fill: parent

                                    Column {
                                        anchors.centerIn: parent // Đảm bảo toàn bộ cục này luôn ở chính giữa
                                        width: parent.width * 0.9 // Chiếm tối đa 90% chiều rộng thẻ để có khoảng lề (padding) 2 bên
                                        spacing: 8

                                        // Biểu tượng (Icon)
                                        Text {
                                            text: "🛎"
                                            font.pixelSize: 45
                                            anchors.horizontalCenter: parent.horizontalCenter
                                        }

                                        // Tên mã phòng (VD: R101)
                                        Text {
                                            text: "R" + model.roomLabel
                                            color: "white"
                                            font.pixelSize: 22
                                            font.bold: true
                                            anchors.horizontalCenter: parent.horizontalCenter
                                        }

                                        // Tên chi tiết phòng
                                        Text {
                                            text: "Room " + model.roomLabel
                                            color: "#9CA3AF"
                                            font.pixelSize: 16

                                            // 3 dòng dưới này RẤT QUAN TRỌNG để co giãn:
                                            width: parent.width // Ép text rộng bằng Column
                                            horizontalAlignment: Text.AlignHCenter // Căn giữa chữ
                                            wrapMode: Text.Wrap // Nếu ô bị thu nhỏ, chữ dài quá sẽ tự động rớt xuống dòng chứ ko chọc thủng viền thẻ
                                        }

                                        // Trạng thái (Chấm xanh + Text)
                                        Row {
                                            spacing: 6
                                            anchors.horizontalCenter: parent.horizontalCenter

                                            Rectangle {
                                                width: 8; height: 8; radius: 4
                                                color: "#10B981"
                                                anchors.verticalCenter: parent.verticalCenter
                                            }

                                            Text {
                                                text: "Available"
                                                color: "#9CA3AF"
                                                font.pixelSize: 12
                                                anchors.verticalCenter: parent.verticalCenter
                                            }
                                        }
                                    }
                                }

                                // 3. Giữ nguyên hoàn toàn logic Click của ông
                                onClicked: {
                                    let newSelection = mainContent.selectedButtonIndices.slice(); // Create a copy

                                    if (newSelection.includes(model.nodeIndex)) {
                                        // Remove index if already selected
                                        newSelection.splice(newSelection.indexOf(model.nodeIndex), 1);
                                    } else {
                                        // Add index if not selected
                                        newSelection.push(model.nodeIndex);
                                    }

                                    mainContent.selectedButtonIndices = newSelection; // Assign new array to trigger updates
                                    console.log("Selected Tables: " + mainContent.selectedButtonIndices);
                                }
                            }
                        }
                    }

//====BẮT ĐẦU PHẦN PORT============
                    // ========================================================
                    // 1. NÚT VUÔNG MÀU XANH (TOGGLE BUTTON) Ở GÓC TRÁI DƯỚI
                    // ========================================================
                    Rectangle {
                        id: toggleBtn
                        width: 60
                        height: 60
                        color: "#165c7d" // Màu xanh dương đậm
                        radius: 15
                        border.color: "black"
                        border.width: 2
                        anchors.left: parent.left
                        anchors.bottom: parent.bottom
                        anchors.margins: 30

                        MouseArea {
                            anchors.fill: parent
                            cursorShape: Qt.PointingHandCursor
                            onClicked: {
                                // Bật/tắt trạng thái hiển thị của bảng COM
                                comPanel.visible = !comPanel.visible
                            }
                        }
                    }

                    // ========================================================
                    // 2. BẢNG SETTING COM (NỔI LÊN KHI BẤM NÚT VUÔNG)
                    // ========================================================
                    Rectangle {
                        id: comPanel
                        visible: false // Mặc định ẩn
                        width: 340
                        height: 280
                        color: "#db7a3b" // Màu cam đất giống thiết kế của bạn
                        radius: 20
                        border.color: "black"
                        border.width: 2

                        // Đặt nó nằm ngay phía trên nút vuông
                        anchors.left: parent.left
                        anchors.bottom: toggleBtn.top
                        anchors.margins: 30
                        anchors.bottomMargin: 10

                        Column {
                            anchors.centerIn: parent
                            spacing: 15

                            // --- Tiêu đề (Header) ---
                            Rectangle {
                                width: 300
                                height: 40
                                color: "#165c7d"
                                border.color: "black"
                                border.width: 2
                                Text {
                                    text: "Action – COM - Status"
                                    color: "white"
                                    font.pixelSize: 20
                                    font.bold: true
                                    anchors.centerIn: parent
                                }
                            }

                            // --- Hàng 1: MOTOR ---
                            Row {
                                spacing: 10

                                // Nút Connect (Có thể gọi hàm Python tại đây)
                                Button {
                                    width: 90; height: 40
                                    background: Rectangle {
                                        color: "#28a745" // Xanh lá
                                        border.color: "black"; border.width: 2
                                    }
                                    contentItem: Text {
                                        text: "Connect"
                                        color: "white"
                                        horizontalAlignment: Text.AlignHCenter
                                        verticalAlignment: Text.AlignVCenter
                                        font.bold: true
                                    }
                                    onClicked: {
                                        // Gọi hàm kết nối riêng lẻ hoặc gọi chung
                                        console.log("Connecting Motor on " + inputMotor.text)
                                    }
                                }

                                // Ô nhập tên cổng COM
                                TextField {
                                    id: inputMotor
                                    width: 80; height: 40
                                    text: "COM1"
                                    font.bold: true
                                    color: "white"
                                    horizontalAlignment: TextInput.AlignHCenter
                                    verticalAlignment: TextInput.AlignVCenter
                                    background: Rectangle {
                                        color: "#165c7d" // Xanh dương
                                        border.color: "black"; border.width: 2
                                    }
                                }

                                // Trạng thái
                                Rectangle {
                                    width: 110; height: 40
                                    color: "#28a745" // Đổi thành màu đỏ/xám nếu ngắt kết nối
                                    border.color: "black"; border.width: 2
                                    Text {
                                        text: "Connected"
                                        color: "white"
                                        font.bold: true
                                        anchors.centerIn: parent
                                    }
                                }
                            }

                            // --- Hàng 2: SENSOR ---
                            Row {
                                spacing: 10
                                Button {
                                    width: 90; height: 40
                                    background: Rectangle { color: "#28a745"; border.color: "black"; border.width: 2 }
                                    contentItem: Text { text: "Connect"; color: "white"; font.bold: true; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
                                }
                                TextField {
                                    id: inputSensor
                                    width: 80; height: 40
                                    text: "COM2"
                                    font.bold: true; color: "white"; horizontalAlignment: TextInput.AlignHCenter; verticalAlignment: TextInput.AlignVCenter
                                    background: Rectangle { color: "#165c7d"; border.color: "black"; border.width: 2 }
                                }
                                Rectangle {
                                    width: 110; height: 40
                                    color: "#28a745"
                                    border.color: "black"; border.width: 2
                                    Text { text: "Connected"; color: "white"; font.bold: true; anchors.centerIn: parent }
                                }
                            }

                            // --- Hàng 3: LASER ---
                            Row {
                                spacing: 10
                                Button {
                                    width: 90; height: 40
                                    background: Rectangle { color: "#28a745"; border.color: "black"; border.width: 2 }
                                    contentItem: Text { text: "Connect"; color: "white"; font.bold: true; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
                                }
                                TextField {
                                    id: inputLaser
                                    width: 80; height: 40
                                    text: "COM11"
                                    font.bold: true; color: "white"; horizontalAlignment: TextInput.AlignHCenter; verticalAlignment: TextInput.AlignVCenter
                                    background: Rectangle { color: "#165c7d"; border.color: "black"; border.width: 2 }
                                }
                                Rectangle {
                                    width: 110; height: 40
                                    color: "#28a745"
                                    border.color: "black"; border.width: 2
                                    Text { text: "Connected"; color: "white"; font.bold: true; anchors.centerIn: parent }
                                }
                            }
                        }
                    }
//================================================================================================================================================
                    //==========KẾT THÚC PHẦN PORT ==================

                    RowLayout {
                        Layout.fillWidth: true
                        Layout.margins: 10
                        spacing: 20
                        anchors.horizontalCenter: parent.horizontalCenter

                        Button {
                            text: "Cancel ❌"
                            Layout.preferredWidth: 100
                            Layout.preferredHeight: 40
                            font.pixelSize: 18

                            background: Rectangle {
                                color: "#27314A"
                                radius: 8
                                border.color: "#3B82F6"
                            }

                            onClicked: {
                                mainContent.selectedButtonIndices = []; // Clear all selections
                                console.log("Selection cleared!");
                            }
                        }

                        Button {
                            text: "Start ✈️"
                            Layout.preferredWidth: 100
                            Layout.preferredHeight: 40
                            font.pixelSize: 18

                            background: Rectangle {
                                color: "#27314A"
                                radius: 8
                                border.color: "#3B82F6"
                            }
                            onClicked: {
                                if (mainContent.selectedButtonIndices.length > 0) {
                                    let selectedTablesArray = mainContent.selectedButtonIndices;
                                    mainContent.selectedButtonIndices = []; // Clear selections
                                    stackView.push(page2)
                                    robotController.run_agv(selectedTablesArray);
                                } else {
                                    console.log("No tables selected!");
                                }
                            }
                        }
                        Button {
                            text: "Led 💡"
                            Layout.preferredWidth: 100
                            Layout.preferredHeight: 40
                            font.pixelSize: 18

                            background: Rectangle {
                                color: "#27314A"
                                radius: 8
                                border.color: "#3B82F6"
                            }

                            onClicked: {
                                turnLedOn.turnOnLed()
                            }
                        }
                        Button {
                            text: "Test 📝"
                            Layout.preferredWidth: 100
                            Layout.preferredHeight: 40
                            font.pixelSize: 18

                            background: Rectangle {
                                color: "#27314A"
                                radius: 8
                                border.color: "#3B82F6"
                            }

                            onClicked: {
                                stackView.push(page4)
                                robotController.run_test()
                            }
                        }
                    }
                }
            }
        }
    }

    Component {
        id: mapPage
        Item {
            width: parent.width
            height: parent.height

            Rectangle {
                anchors.fill: parent
                color: "#F8F9FA"

                ColumnLayout {
                    anchors.fill: parent
                    spacing: 0

                    Rectangle {
                        Layout.fillWidth: true
                        height: 82
                        color: "white"
                        border.color: "#E5E7EB"
                        border.width: 1

                        Text {
                            anchors.left: parent.left
                            anchors.leftMargin: 24
                            anchors.verticalCenter: parent.verticalCenter
                            text: "Robot Map"
                            font.pixelSize: 28
                            font.bold: true
                            color: "#374151"
                        }

                        Row {
                            anchors.right: parent.right
                            anchors.rightMargin: 24
                            anchors.verticalCenter: parent.verticalCenter
                            spacing: 12

                            Button {
                                text: "-"
                                width: 56
                                height: 48
                                font.pixelSize: 22
                                font.bold: true
                                onClicked: mapViewFlickable.mapScale =
                                           Math.max(0.2, mapViewFlickable.mapScale - 0.2)
                            }
                            Text {
                                anchors.verticalCenter: parent.verticalCenter
                                text: Math.round(mapViewFlickable.mapScale * 100) + "%"
                                width: 64
                                horizontalAlignment: Text.AlignHCenter
                                font.pixelSize: 17
                                font.bold: true
                                color: "#374151"
                            }
                            Button {
                                text: "+"
                                width: 56
                                height: 48
                                font.pixelSize: 22
                                font.bold: true
                                onClicked: mapViewFlickable.mapScale =
                                           Math.min(4.0, mapViewFlickable.mapScale + 0.2)
                            }
                            Button {
                                text: "Reset View"
                                width: 120
                                height: 48
                                font.pixelSize: 16
                                onClicked: {
                                    mapViewFlickable.mapScale = 1.0
                                    mapViewFlickable.contentX = 0
                                    mapViewFlickable.contentY = 0
                                }
                            }
                            Button {
                                text: "History"
                                width: 100
                                height: 48
                                font.pixelSize: 16
                                onClicked: stackView.push(mapHistoryPage)
                            }
                            Button {
                                text: "Adjust Map"
                                width: 130
                                height: 48
                                font.pixelSize: 16
                                font.bold: true
                                highlighted: true
                                onClicked: stackView.push(mapEditPage)
                            }
                            Button {
                                text: "X"
                                width: 60
                                height: 48
                                font.pixelSize: 16
                                onClicked: stackView.pop()
                            }
                        }
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        height: 58
                        color: "#F3F4F6"
                        border.color: "#E5E7EB"

                        Row {
                            anchors.centerIn: parent
                            spacing: 32

                            Repeater {
                                model: [
                                    { name: "Path", color: "#000000" },
                                    { name: "Pavement", color: "#D1D5DB" },
                                    { name: "Destination", color: "#EF4444" },
                                    { name: "Starting point", color: "#22C55E" }
                                ]

                                delegate: Row {
                                    spacing: 8
                                    Rectangle {
                                        width: 18
                                        height: 18
                                        radius: 4
                                        color: modelData.color
                                        anchors.verticalCenter: parent.verticalCenter
                                    }
                                    Text {
                                        text: modelData.name
                                        color: "#374151"
                                        font.pixelSize: 16
                                        font.bold: true
                                        anchors.verticalCenter: parent.verticalCenter
                                    }
                                }
                            }
                        }
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        color: "#9CA3AF"

                        Flickable {
                            id: mapViewFlickable
                            anchors.fill: parent
                            clip: true
                            interactive: true
                            boundsBehavior: Flickable.StopAtBounds

                            property real mapScale: 1.0
                            property real cellSize: 40

                            contentWidth: Math.max(width, mapViewGrid.width * mapScale)
                            contentHeight: Math.max(height, mapViewGrid.height * mapScale)

                            ScrollBar.vertical: ScrollBar { width: 15 }
                            ScrollBar.horizontal: ScrollBar { height: 15 }

                            WheelHandler {
                                onWheel: function(event) {
                                    let delta = event.angleDelta.y > 0 ? 0.1 : -0.1
                                    mapViewFlickable.mapScale =
                                        Math.max(0.2, Math.min(4.0, mapViewFlickable.mapScale + delta))
                                }
                            }

                            GridView {
                                id: mapViewGrid
                                width: app.mapColCount * mapViewFlickable.cellSize
                                height: app.mapRowCount * mapViewFlickable.cellSize
                                x: Math.max(0, (mapViewFlickable.width - width * scale) / 2) / scale
                                y: Math.max(0, (mapViewFlickable.height - height * scale) / 2) / scale
                                transformOrigin: Item.TopLeft
                                scale: mapViewFlickable.mapScale
                                model: mapSharedModel
                                interactive: false
                                cellWidth: mapViewFlickable.cellSize
                                cellHeight: mapViewFlickable.cellSize

                                delegate: Rectangle {
                                    width: mapViewGrid.cellWidth
                                    height: mapViewGrid.cellHeight
                                    border.color: "#E5E7EB"
                                    border.width: 1
                                    color: {
                                        if (model.cellType === 0) return "#000000"
                                        if (model.cellType === 1) return "#D1D5DB"
                                        if (model.cellType === 2) return "#EF4444"
                                        if (model.cellType === 3) return "#22C55E"
                                        return "white"
                                    }

                                    Text {
                                        anchors.centerIn: parent
                                        text: model.cellType === 2 ? model.destNumber : ""
                                        color: "white"
                                        font.pixelSize: 12
                                        font.bold: true
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    Component {
        id: mapHistoryPage
        Item {
            width: parent.width
            height: parent.height

            Component.onCompleted: app.refreshMapHistory()

            Rectangle {
                anchors.fill: parent
                color: "#F8F9FA"

                ColumnLayout {
                    anchors.fill: parent
                    spacing: 0

                    Rectangle {
                        Layout.fillWidth: true
                        height: 64
                        color: "white"
                        border.color: "#E5E7EB"

                        Text {
                            anchors.left: parent.left
                            anchors.leftMargin: 20
                            anchors.verticalCenter: parent.verticalCenter
                            text: "Map History"
                            font.pixelSize: 22
                            font.bold: true
                            color: "#374151"
                        }

                        Row {
                            anchors.right: parent.right
                            anchors.rightMargin: 20
                            anchors.verticalCenter: parent.verticalCenter
                            spacing: 10

                            Button {
                                text: "Refresh"
                                onClicked: app.refreshMapHistory()
                            }
                            Button {
                                text: "[X]"
                                onClicked: stackView.pop()
                            }
                        }
                    }

                    Text {
                        Layout.fillWidth: true
                        Layout.margins: 20
                        visible: mapHistoryModel.count === 0
                        text: "No saved map history yet."
                        horizontalAlignment: Text.AlignHCenter
                        color: "#6B7280"
                        font.pixelSize: 16
                    }

                    ListView {
                        id: historyList
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        Layout.margins: 20
                        spacing: 10
                        clip: true
                        model: mapHistoryModel

                        delegate: Rectangle {
                            width: historyList.width
                            height: 86
                            radius: 10
                            color: "white"
                            border.color: "#D1D5DB"

                            RowLayout {
                                anchors.fill: parent
                                anchors.margins: 14
                                spacing: 18

                                ColumnLayout {
                                    Layout.fillWidth: true
                                    spacing: 5

                                    Text {
                                        text: model.historyLabel + " - " +
                                              model.createdAt.replace("T", " ")
                                        color: "#111827"
                                        font.pixelSize: 16
                                        font.bold: true
                                    }
                                    Text {
                                        text: model.rowCount + " x " + model.columnCount +
                                              " | Starts: " + model.startCount +
                                              " | Destinations: " + model.goalCount
                                        color: "#6B7280"
                                        font.pixelSize: 14
                                    }
                                }

                                Button {
                                    text: "Restore"
                                    highlighted: true
                                    onClicked: {
                                        let restored =
                                            robotController.restore_map_history(model.snapshotId)
                                        if (restored !== "") {
                                            app.applyMapState(restored)
                                            app.refreshMapHistory()
                                            stackView.pop()
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    Component {
        id: mapEditPage
        Item {
            width: parent.width
            height: parent.height

            // Các biến trạng thái của Map
            property int colCount: 20  // Số cột mặc định
            property int rowCount: 10  // Số hàng mặc định
            property string saveError: ""
            // 0: Path (Đen), 1: Pavement (Xám), 2: Destination (Đỏ), 3: Start (Xanh)
            property int currentTool: 1

            Rectangle {
                anchors.fill: parent
                color: "#F8F9FA" // Nền trắng/xám nhạt giống ảnh

                ColumnLayout {
                    anchors.fill: parent
                    spacing: 0

                    // === TOOLBAR TRÊN CÙNG ===
                    Rectangle {
                        Layout.fillWidth: true
                        height: 82
                        color: "white"
                        border.color: "#E5E7EB"
                        border.width: 1

                        Row {
                            anchors.left: parent.left
                            anchors.verticalCenter: parent.verticalCenter
                            anchors.leftMargin: 24
                            Text {
                                text: "Adjust Robot Map"
                                font.pixelSize: 28
                                font.bold: true
                                color: "#374151"
                            }
                        }

                        Row {
                            anchors.right: parent.right
                            anchors.verticalCenter: parent.verticalCenter
                            anchors.rightMargin: 24
                            spacing: 12

                            // CỤM NÚT ZOOM MAP
                            Button {
                                text: "-"
                                width: 56
                                height: 48
                                font.pixelSize: 22
                                font.bold: true
                                background: Rectangle { color: "#0a0a0a"; radius: 8 }
                                onClicked: mapFlickable.mapScale = Math.max(0.2, mapFlickable.mapScale - 0.2)
                            }
                            Text {
                                text: Math.round(mapFlickable.mapScale * 100) + "%"
                                width: 64
                                horizontalAlignment: Text.AlignHCenter
                                font.pixelSize: 17
                                font.bold: true
                                color: "#374151"
                                anchors.verticalCenter: parent.verticalCenter
                            }
                            Button {
                                text: "+"
                                width: 56
                                height: 48
                                font.pixelSize: 22
                                font.bold: true
                                background: Rectangle { color: "#09090a"; radius: 8 }
                                onClicked: mapFlickable.mapScale = Math.min(4.0, mapFlickable.mapScale + 0.2)
                            }

                            // Khoảng cách tách biệt với các nút Tool
                            Item { width: 10; height: 1 }


                            // Nút Back
                            Button {
                                text: "X"
                                width: 86
                                height: 48
                                font.pixelSize: 16
                                background: Rectangle { color: "#101112"; radius: 10 }
                                onClicked: stackView.pop()
                            }

                            // Công cụ vẽ (Tools)
                            Repeater {
                                model: [
                                    { name: "Starting point", color: "#22C55E", toolId: 3 },
                                    { name: "Pavement", color: "#9CA3AF", toolId: 1 },
                                    { name: "Path", color: "#000000", toolId: 0 },
                                    { name: "Destinations", color: "#EF4444", toolId: 2 }
                                ]
                                delegate: Button {
                                    text: modelData.name
                                    width: 132
                                    height: 48
                                    contentItem: Text {
                                        text: parent.text
                                        color: "white"
                                        font.pixelSize: 16
                                        font.bold: true
                                        horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter
                                    }
                                    background: Rectangle {
                                        color: modelData.color
                                        radius: 10
                                        // Viền phát sáng nếu đang được chọn
                                        border.color: currentTool === modelData.toolId ? "#3B82F6" : "transparent"
                                        border.width: currentTool === modelData.toolId ? 3 : 0
                                    }
                                    onClicked: currentTool = modelData.toolId
                                }
                            }

                            // Nút Save (In ra console và gửi Python)
                            Button {
                                text: "Save Map"
                                width: 120
                                height: 48
                                font.pixelSize: 16
                                font.bold: true
                                background: Rectangle { color: "#0e0e0f"; radius: 10; border.color: "#D1D5DB" }
                                onClicked: {
                                    let mapMatrix = []
                                    let starts = []
                                    let rawGoals = [] // Mảng trung gian để sort

                                    for (let r = 0; r < app.mapRowCount; r++) {
                                        let rowData = []
                                        for (let c = 0; c < app.mapColCount; c++) {
                                            let item = mapSharedModel.get(r * app.mapColCount + c)
                                            rowData.push(item.cellType)

                                            if (item.cellType === 3) starts.push([r, c])
                                            if (item.cellType === 2) {
                                                // Chuyển chữ thành số để so sánh (Nếu ô trống thì để 999999 cho nó bị đẩy xuống cuối)
                                                let numStr = item.destNumber
                                                let numVal = parseInt(numStr)
                                                if (isNaN(numVal)) numVal = 999999

                                                rawGoals.push({ r: r, c: c, numVal: numVal, label: numStr })
                                            }
                                        }
                                        mapMatrix.push(rowData)
                                    }

                                    // TIẾN HÀNH SORT CÁC DESTINATION TĂNG DẦN THEO SỐ ĐÃ NHẬP
                                    rawGoals.sort((a, b) => a.numVal - b.numVal)

                                    // Lọc lại mảng theo đúng định dạng gửi sang Python: [row, col, "Tên phòng"]
                                    let goals = rawGoals.map(g => [g.r, g.c, g.label])

                                    let errorMessage = robotController.save_map_data(
                                        JSON.stringify(mapMatrix),
                                        JSON.stringify(starts),
                                        JSON.stringify(goals)
                                    )
                                    if (errorMessage === "") {
                                        saveError = ""
                                        app.applyMapState({
                                            matrix: mapMatrix,
                                            starts: starts,
                                            goals: goals
                                        })
                                        console.log("Đã lưu map và tạo lại chỉ dẫn thành công!")
                                        stackView.pop()
                                    } else {
                                        saveError = errorMessage
                                    }
                                }
                            }
                        }
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        height: saveError === "" ? 0 : 52
                        visible: saveError !== ""
                        color: "#FEE2E2"
                        border.color: "#FCA5A5"

                        Text {
                            anchors.fill: parent
                            anchors.margins: 10
                            text: "Cannot save map: " + saveError
                            color: "#991B1B"
                            font.pixelSize: 15
                            font.bold: true
                            elide: Text.ElideRight
                            verticalAlignment: Text.AlignVCenter
                        }
                    }

                    // === THANH SETTING SỐ HÀNG / CỘT ===
                    Rectangle {
                        Layout.fillWidth: true
                        height: 70
                        color: "white"
                        border.color: "#E5E7EB"

                        RowLayout {
                            anchors.fill: parent
                            anchors.margins: 11
                            spacing: 14

                            TextField {
                                id: colInput
                                Layout.fillWidth: true
                                Layout.preferredHeight: 48
                                placeholderText: "Number of columns (VD: 20)"
                                text: "20"
                                font.pixelSize: 16
                                validator: IntValidator { bottom: 1; top: 100 }
                            }
                            TextField {
                                id: rowInput
                                Layout.fillWidth: true
                                Layout.preferredHeight: 48
                                placeholderText: "Number of rows (VD: 10)"
                                text: "10"
                                font.pixelSize: 16
                                validator: IntValidator { bottom: 1; top: 100 }
                            }
                            Button {
                                text: "Set Grid"
                                Layout.preferredWidth: 120
                                Layout.preferredHeight: 48
                                font.pixelSize: 16
                                font.bold: true
                                onClicked: {
                                    // Cập nhật biến toàn cục thay vì biến cục bộ
                                    app.mapColCount = parseInt(colInput.text) || 20
                                    app.mapRowCount = parseInt(rowInput.text) || 10

                                    let fitWidth = mapFlickable.width / app.mapColCount
                                    let fitHeight = mapFlickable.height / app.mapRowCount
                                    mapFlickable.cellSize = Math.min(fitWidth, fitHeight)

                                    mapFlickable.mapScale = 1.0
                                    mapFlickable.contentX = 0
                                    mapFlickable.contentY = 0

                                    // Reset lại dữ liệu của mapSharedModel
                                    mapSharedModel.clear()
                                    for(let i = 0; i < app.mapColCount * app.mapRowCount; i++) {
                                        mapSharedModel.append({ cellType: 1, destNumber: "" })
                                    }
                                }
                            }
                        }
                    }

                    // === KHU VỰC VẼ GRID ===
                    Rectangle {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        color: "#9CA3AF" // Đổi màu viền ngoài cùng thành xám tối để làm nổi bản đồ

                        // Khung cuộn bản đồ
                        Flickable {
                            id: mapFlickable
                            anchors.fill: parent
                            clip: true

                            property real mapScale: 1.0
                            property real cellSize: 40 // CHỐT CỨNG Ô VUÔNG 40x40

                            // Tính toán kích thước thật của bản đồ sau khi Zoom
                            contentWidth: mapGrid.width * mapScale
                            contentHeight: mapGrid.height * mapScale

                            // Thanh cuộn ngang & dọc
                            ScrollBar.vertical: ScrollBar { width: 15 }
                            ScrollBar.horizontal: ScrollBar { height: 15 }

                            // Đã sửa cú pháp WheelHandler
                            WheelHandler {
                                onWheel: function(event) {
                                    let zoomSpeed = 0.1
                                    let newScale = event.angleDelta.y > 0
                                                   ? mapFlickable.mapScale + zoomSpeed
                                                   : mapFlickable.mapScale - zoomSpeed

                                    // Chặn Zoom tối thiểu 20% và tối đa 400%
                                    if (newScale >= 0.2 && newScale <= 4.0) {
                                        mapFlickable.mapScale = newScale
                                    }
                                }
                            }

                            GridView {
                                id: mapGrid
                                width: app.mapColCount * mapFlickable.cellSize
                                height: app.mapRowCount * mapFlickable.cellSize

                                // === CÔNG THỨC ÉP BẢN ĐỒ RA GIỮA KHUNG NHÌN ===
                                x: Math.max(0, (mapFlickable.width - (width * scale)) / 2) / scale
                                y: Math.max(0, (mapFlickable.height - (height * scale)) / 2) / scale

                                transformOrigin: Item.TopLeft
                                scale: mapFlickable.mapScale

                                // GÁN ĐÚNG MODEL MAP CHUNG
                                model: mapSharedModel

                                interactive: false // Tắt tính năng cuộn nội tại của GridView
                                cellWidth: mapFlickable.cellSize
                                cellHeight: mapFlickable.cellSize

                                delegate: Rectangle {
                                    width: mapGrid.cellWidth
                                    height: mapGrid.cellHeight
                                    border.color: "#E5E7EB"
                                    border.width: 1

                                    color: {
                                        if (model.cellType === 0) return "#000000" // Path
                                        if (model.cellType === 1) return "#D1D5DB" // Pavement
                                        if (model.cellType === 2) return "#EF4444" // Goal
                                        if (model.cellType === 3) return "#22C55E" // Start
                                        return "white"
                                    }

                                    MouseArea {
                                        anchors.fill: parent
                                        hoverEnabled: true
                                        acceptedButtons: Qt.LeftButton | Qt.RightButton
                                        drag.threshold: 1          // Cực kỳ nhạy, di 1 pixel là nhận luôn
                                        preventStealing: true      // Không để Flickable "cướp" sự kiện chuột khi đang vẽ

                                        // Các biến lưu trạng thái neo cố định lúc bắt đầu ấn chuột
                                        property point pressViewportPos
                                        property real pressContentX
                                        property real pressContentY

                                        onPressed: function(mouse) {
                                            // Chặn sự kiện click để nhường cho ô gõ chữ
                                            if (mouse.button === Qt.LeftButton && currentTool === 2 && model.cellType === 2) {
                                                numInput.forceActiveFocus()
                                                mouse.accepted = false
                                                return;
                                            }

                                            if (mouse.button === Qt.RightButton) {
                                                pressViewportPos = mapToItem(mapFlickable, mouse.x, mouse.y)
                                                pressContentX = mapFlickable.contentX
                                                pressContentY = mapFlickable.contentY
                                            } else if (mouse.button === Qt.LeftButton) {
                                                mapSharedModel.setProperty(index, "cellType", currentTool)
                                                if (currentTool !== 2) {
                                                    mapSharedModel.setProperty(index, "destNumber", "")
                                                }
                                            }
                                        }

                                        onPositionChanged: function(mouse) {
                                            if (pressed && pressedButtons === Qt.LeftButton) {
                                                let mappedPos = mapToItem(mapGrid, mouse.x, mouse.y)
                                                let hoveredIndex = mapGrid.indexAt(mappedPos.x, mappedPos.y)
                                                if (hoveredIndex !== -1) {
                                                    mapSharedModel.setProperty(hoveredIndex, "cellType", currentTool)
                                                }
                                            }
                                            else if (pressed && pressedButtons === Qt.RightButton) {
                                                let currentViewportPos = mapToItem(mapFlickable, mouse.x, mouse.y)
                                                let dx = currentViewportPos.x - pressViewportPos.x
                                                let dy = currentViewportPos.y - pressViewportPos.y

                                                mapFlickable.contentX = Math.max(0, Math.min(mapFlickable.contentWidth - mapFlickable.width, pressContentX - dx))
                                                mapFlickable.contentY = Math.max(0, Math.min(mapFlickable.contentHeight - mapFlickable.height, pressContentY - dy))
                                            }
                                        }
                                    }

                                    // Ô NHẬP SỐ CHO DESTINATION
                                    TextInput {
                                        id: numInput
                                        anchors.centerIn: parent
                                        width: parent.width - 2
                                        horizontalAlignment: Text.AlignHCenter
                                        color: "white"
                                        font.pixelSize: 12
                                        font.bold: true

                                        // Nổi lên trên để click được
                                        z: 10

                                        // Chỉ hiện và cho phép gõ khi ô đó được tô màu đỏ (2)
                                        visible: model.cellType === 2
                                        enabled: model.cellType === 2

                                        // Đọc dữ liệu từ model
                                        text: model.destNumber

                                        // Ghi dữ liệu vào model mỗi khi ông gõ phím
                                        onTextEdited: {
                                           mapSharedModel.setProperty(index, "destNumber", text)
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    Component {
        id: page2
        Item {
            width: parent.width
            height: parent.height

            Rectangle {
                width: parent.width
                height: parent.height
                color: "#1B2236"

                Column {
                    anchors.centerIn: parent
                    spacing: 20  // Ensure there's some space between the text and button

                    Text {
                        anchors.horizontalCenter: parent.horizontalCenter
                        text: "Waiting for deliver..."
                        color: "White"
                        font.bold: true
                        font.pixelSize: 24
                    }

                    Rectangle {
                        anchors.horizontalCenter: parent.horizontalCenter
                        width: 70
                        height: 50
                        color: "red"
                        radius: 10  // Add a small radius for rounded corners
                        Text {
                            color: "White"
                            anchors.centerIn: parent
                            text: "STOP"
                            font.pixelSize: 24
                            font.bold: true
                        }
                        MouseArea {
                            anchors.fill: parent
                            onClicked: {
                                stackView.push(page3)
                                console.log ("Stop")
                                robotController.stop_agv()
                            }
                        }
                    }
                }
            }
        }
    }

    Component {
        id: page3
        Item {
            width: parent.width
            height: parent.height

            Rectangle {
                width: parent.width
                height: parent.height
                color: "#1B2236"

                Column {
                    anchors.centerIn: parent
                    spacing: 20  // Ensure there's some space between the text and button

                    Text {
                        id: messageText
                        anchors.horizontalCenter: parent.horizontalCenter
                        text: "Make choice..."
                        color: "White"
                        font.bold: true
                        font.pixelSize: 24
                    }

                    Rectangle {
                        id: continue111
                        anchors.horizontalCenter: parent.horizontalCenter
                        width: 130
                        height: 50
                        color: "red"
                        radius: 10  // Add a small radius for rounded corners
                        Text {
                            color: "White"
                            anchors.centerIn: parent
                            text: "CONTINUE"
                            font.pixelSize: 24
                            font.bold: true
                        }
                        MouseArea {
                            anchors.fill: parent
                            onClicked: {
                                stackView.push(page2)
                                console.log ("Continue")
                                robotController.continue_agv()
                            }
                        }
                    }
                    Rectangle {
                        id: return111
                        anchors.horizontalCenter: parent.horizontalCenter
                        width: 250
                        height: 50
                        color: "red"
                        radius: 10  // Add a small radius for rounded corners
                        Text {
                            color: "White"
                            anchors.centerIn: parent
                            text: "RETURN TO KITCHEN"
                            font.pixelSize: 24
                            font.bold: true
                        }
                        MouseArea {
                            anchors.fill: parent
                            onClicked: {
                                continue111.enabled = false
                                continue111.visible = false
                                return111.enabled = false
                                return111.visible = false
                                messageText.text = "Returning to Kitchen..."  // Change the text here
                                robotController.return_to_kitchen()
                                console.log ("Return")
                            }
                        }
                    }
                }
            }
        }
    }

    Component {
        id: page4
        Item {
            width: parent.width
            height: parent.height

            Rectangle {
                width: parent.width
                height: parent.height
                color: "#1B2236"

                Column {
                    anchors.centerIn: parent
                    spacing: 20  // Ensure there's some space between the text and button

                    Text {
                        anchors.horizontalCenter: parent.horizontalCenter
                        text: "Testing..."
                        color: "White"
                        font.bold: true
                        font.pixelSize: 24
                    }

                    Rectangle {
                        anchors.horizontalCenter: parent.horizontalCenter
                        width: 130
                        height: 50
                        color: "red"
                        radius: 10  // Add a small radius for rounded corners
                        Text {
                            color: "White"
                            anchors.centerIn: parent
                            text: "STOP TEST"
                            font.pixelSize: 24
                            font.bold: true
                        }
                        MouseArea {
                            anchors.fill: parent
                            onClicked: {
                                console.log ("Stop")
                                robotController.disable_test_run()
                            }
                        }
                    }
                }
            }
        }
    }
}
