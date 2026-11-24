import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Window
import "Pearl.js" as Pearl

ApplicationWindow {
    id: root
    objectName: "previewWindow"
    width: 1280; height: 900
    minimumWidth: 1020; minimumHeight: 740
    visible: true
    title: preview.isDemo ? "政策周报 · 界面预览" : "政策周报"
    color: Pearl.paper
    palette.window: Pearl.paper
    palette.windowText: Pearl.ink
    palette.text: Pearl.ink
    palette.highlight: Pearl.accent
    palette.highlightedText: "#ffffff"
    palette.accent: Pearl.accent
    palette.button: Pearl.surface
    palette.buttonText: Pearl.ink
    palette.link: Pearl.active
    palette.base: Pearl.surface
    font.family: workspaceFonts.sans
    font.pixelSize: 13
    property int page: 0
    property bool siteMapMode: true
    property bool reducedMotion: false
    property bool reducedTransparency: !preview.shaderSupported
    property string drawer: ""
    property bool inspectLastTask: false
    property bool technicalDetails: false
    onTechnicalDetailsChanged: { if (technicalDetails && logs.followTail) Qt.callLater(function(){logs.positionViewAtEnd()}) }
    readonly property bool showMonitor: preview.running || (inspectLastTask && preview.hasTask)
    function toggleDrawer(key) { drawer = drawer === key ? "" : key }
    readonly property string serif: workspaceFonts.serif
    property real introProgress: 0
    readonly property int introDuration: 1800
    readonly property real reveal: booting ? startup.workspaceReveal : 1
    property bool booting: false
    property string toastText: ""
    property bool toastShown: false
    property bool settingsReady: false
    readonly property var updates: preview.updater
    property string desiredModel: ""
    readonly property int activeRecentDays: matchesRecentDays(7) ? 7 : matchesRecentDays(30) ? 30 : 0
    property var pageTitles: ["采集工作台", "站点管理", "历史报告", "偏好设置"]
    property var pageLabels: ["采集任务", "站点管理", "历史报告", "设置"]
    function replayIntro() {
        if (preview.running) return
        if (reducedMotion) { finishIntro(); return }
        intro.stop(); page=0; inspectLastTask=false; introProgress=0; booting=true
        startup.forceActiveFocus()
        intro.start()
    }
    function recentRange(days) {
        let end = new Date(); end.setDate(end.getDate() - 1)
        let start = new Date(end); start.setDate(start.getDate() - days + 1)
        return { start: startDate.format(start), end: endDate.format(end) }
    }
    function matchesRecentDays(days) {
        let range = recentRange(days)
        return startDate.value === range.start && endDate.value === range.end
    }
    function recentDays(days) {
        let range = recentRange(days)
        startDate.value = range.start; endDate.value = range.end
    }
    function finishIntro() {
        intro.stop(); introProgress=1; booting=false
    }
    function currentOptions() {
        return {
            start_date: startDate.value, end_date: endDate.value,
            openai_base_url: apiUrl.text, openai_api_key: apiKey.text, openai_model: modelBox.currentText,
            use_llm: llmEnabled.checked, download_attachments: attachments.checked,
            browser_fallback: browserFallback.checked, strict_mode: strictMode.checked,
            verify_ssl: verifySsl.checked, allow_rule_fallback: ruleFallback.checked,
            sleep_seconds: interval.value / 10, reduced_motion: root.reducedMotion,
            reduced_transparency: root.reducedTransparency
        }
    }
    function queueSave() { if (settingsReady && !preview.isDemo) saveTimer.restart() }
    function selectSavedModel() {
        let model = root.desiredModel || modelBox.currentText
        let index = preview.modelOptions.indexOf(model)
        if (index < 0) index = preview.modelOptions.indexOf(root.desiredModel)
        modelBox.currentIndex = index >= 0 ? index : preview.modelOptions.length ? 0 : -1
    }
    Component.onCompleted: {
        recentDays(7)
        let s = preview.initialSettings
        if (s.start_date) startDate.value = s.start_date
        if (s.end_date) endDate.value = s.end_date
        apiUrl.text = s.openai_base_url || ""
        apiKey.text = s.openai_api_key || ""
        root.desiredModel = s.openai_model || ""
        llmEnabled.checked = s.use_llm === undefined ? true : s.use_llm
        attachments.checked = s.download_attachments === undefined ? false : s.download_attachments
        browserFallback.checked = s.browser_fallback === undefined ? true : s.browser_fallback
        strictMode.checked = s.strict_mode === undefined ? true : s.strict_mode
        verifySsl.checked = s.verify_ssl === undefined ? true : s.verify_ssl
        ruleFallback.checked = s.allow_rule_fallback || false
        interval.value = s.sleep_seconds === undefined ? 5 : Math.round(s.sleep_seconds * 10)
        root.reducedMotion = s.reduced_motion || false
        root.reducedTransparency = !preview.shaderSupported || s.reduced_transparency || false
        selectSavedModel()
        settingsReady = true
        replayIntro()
    }
    onReducedMotionChanged: { if (booting && reducedMotion) finishIntro(); queueSave() }
    onReducedTransparencyChanged: queueSave()
    onPageChanged: { if (settingsReady && page === 2) preview.refreshReports() }
    onClosing: function(close) {
        if (settingsReady) preview.saveConfig(root.currentOptions())
        if (preview.running) { close.accepted = false; exitDialog.open() }
    }
    Shortcut {
        sequences: [StandardKey.Close]
        context: Qt.WindowShortcut
        onActivated: root.close()
    }
    Timer { id: saveTimer; interval: 450; onTriggered: preview.saveConfig(root.currentOptions()) }
    Connections { target: sources; function onSelectionChanged() { root.queueSave() } }
    SequentialAnimation {
        id: intro
        NumberAnimation { target: root; property: "introProgress"; from: 0; to: 1; duration: root.introDuration; easing.type: Easing.Linear }
        ScriptAction { script: root.booting = false }
    }
    Connections {
        target: preview
        function onToast(message) { root.toastText = message; root.toastShown = true; toastTimer.restart() }
        function onLogAdded() { if (root.technicalDetails && logs.followTail) Qt.callLater(function() { if(logs.followTail) logs.positionViewAtEnd() }) }
        function onModelsChanged() { Qt.callLater(function() { root.selectSavedModel(); root.queueSave() }) }
        function onCloseReady() { root.close() }
        function onApiBaseResolved(url) { apiUrl.text = url }
    }
    Timer { id: toastTimer; interval: 3500; onTriggered: root.toastShown = false }

    Item {
        id: scenery
        anchors.fill: parent
        clip: true
        Rectangle { anchors.fill: parent; color: Pearl.surface }
    }
    ShaderEffectSource {
        id: backdropTexture
        sourceItem: scenery
        live: true
        hideSource: false
        visible: false
        textureSize: Qt.size(root.width, root.height)
    }
    Rectangle {
        y: 65; width: parent.width; height: parent.height - y
        color: Pearl.paper
    }

    component SmallLabel: Text {
        color: Pearl.muted
        font.pixelSize: 12
    }
    component DatePreset: AppButton {
        id: preset
        required property int days
        readonly property bool selected: root.activeRecentDays === days
        text: "近 " + days + " 天"
        compact: true
        tone: "ghost"
        Accessible.checkable: true
        Accessible.checked: selected
        background: Rectangle {
            radius: 6
            color: preset.selected ? (preset.down ? Pearl.line : Pearl.soft)
                 : preset.down ? Pearl.line : preset.hovered ? Pearl.soft : "transparent"
            border.width: 1
            border.color: preset.selected ? Pearl.frame : preset.activeFocus ? Pearl.accent : "transparent"
            Behavior on color { ColorAnimation { duration: root.reducedMotion ? 0 : 120 } }
        }
        onClicked: root.recentDays(days)
    }
    component Separator: Rectangle {
        Layout.fillWidth: true
        implicitHeight: 1
        color: Pearl.line
    }
    component SettingPair: RowLayout {
        property string label: ""
        property alias checked: switcher.checked
        Layout.fillWidth: true
        Layout.minimumHeight: 32
        spacing: 8
        Text { text: label; color: Pearl.ink; font.pixelSize: 12; Layout.fillWidth: true }
        Toggle { id: switcher; Accessible.name: label }
    }

    ColumnLayout {
        id: shell
        anchors.fill: parent
        spacing: 0
        opacity: root.reveal
        Item {
            Layout.fillWidth: true; Layout.preferredHeight: 65
            RowLayout {
                anchors { left: parent.left; leftMargin: 28; verticalCenter: parent.verticalCenter }
                spacing: 10
                Rectangle {
                    width: 30; height: 34; radius: 5; color: Pearl.soft
                    Icon { anchors.centerIn: parent; name: "file-text"; tint: Pearl.muted; width: 19; height: 19 }
                }
                ColumnLayout {
                    spacing: 2
                    Text { id: brandTitle; objectName: "brandTitle"; text: "政策周报"; color: Pearl.ink; font.family:root.serif; font.pixelSize: 23; font.weight: Font.DemiBold; opacity:root.booting ? 0 : 1 }
                }
            }
            Loader {
                anchors.left: parent.left; anchors.leftMargin: 210; anchors.verticalCenter: parent.verticalCenter
                sourceComponent: GlassNavigation {
                    id: mainNavigation; objectName: "mainNavigation"
                    currentIndex: root.page
                    reducedMotion: root.reducedMotion
                    reducedTransparency: root.reducedTransparency
                    texture: backdropTexture; scene: root.contentItem
                    onChosen: function(index) { root.page = index }
                }
            }
            RowLayout {
                anchors { right: parent.right; rightMargin: 28; verticalCenter: parent.verticalCenter }
                spacing: 12
                Text { visible:preview.isDemo; text:"离线演示"; color:Pearl.active; font.pixelSize:11 }
                AppButton { iconName: "rotate-ccw"; tone: "ghost"; hint: "重播启动动画"; enabled:!preview.running; onClicked: root.replayIntro() }
            }
        }
        ColumnLayout {
            Layout.fillHeight: true; Layout.fillWidth: true
            spacing: 0
            Rectangle {
                Layout.fillWidth: true; height: 1; color: "#80ffffff"
            }
            Item {
                Layout.fillWidth: true; Layout.preferredHeight: root.page === 0 ? 70 : 64
                ColumnLayout {
                    anchors { left: parent.left; leftMargin: 30; verticalCenter: parent.verticalCenter }
                    spacing: 6
                    Text { text: root.page === 0 ? "本期政策周报" : root.pageTitles[root.page]; color: Pearl.ink; font.family:root.serif; font.pixelSize: root.page === 0 ? 32 : 25; font.weight: Font.DemiBold }
                }
                RowLayout {
                    anchors { right: parent.right; rightMargin: 30; verticalCenter: parent.verticalCenter }
                    spacing: 12
                    AppButton {
                        objectName: "openLastPdf"; visible: !preview.isDemo && preview.lastPdf.length > 0
                        text: "打开本次 PDF"; iconName: "external-link"
                        onClicked: preview.openFile(preview.lastPdf)
                    }
                    AppButton {
                        objectName: "availableUpdate"; visible: !!root.updates && root.updates.available
                        iconName: "arrow-down"; tone: "ghost"; hint: "有可用更新"
                        implicitWidth:40; implicitHeight:40
                        background: Item { Rectangle { anchors.centerIn:parent; width:30; height:30; radius:15; border.color:Pearl.frame; color:parent.parent.hovered ? Pearl.soft : Pearl.surface } }
                        onClicked: updateDialog.open()
                    }
                    AppButton {
                        objectName: "startButton"
                        visible: root.page === 0
                        text: preview.stopping ? "正在停止" : preview.running ? "停止" : preview.isDemo ? "开始演示" : "开始生成"
                        iconName: preview.running ? "square" : "play"
                        tone: preview.running ? "danger" : "primary"
                        enabled: !preview.stopping && !preview.modelsLoading && !preview.modelTesting && (preview.running || (sources.selectedCount > 0 && calendarArc.valid))
                        onClicked: preview.running ? preview.stop() : preview.start(startDate.value, endDate.value, root.currentOptions())
                    }
                }
            }
            Separator {}
            Item {
                id: pages
                Layout.fillWidth: true; Layout.fillHeight: true

                ColumnLayout {
                    id: collectionPage
                    anchors.fill: parent
                    opacity: root.page === 0 ? 1 : 0
                    visible: opacity > 0
                    enabled: root.page === 0
                    Behavior on opacity { NumberAnimation { duration: root.reducedMotion ? 0 : 170 } }
                    spacing: 0
                    RowLayout {
                        readonly property bool needsSpace: root.showMonitor || root.drawer !== "" || !logToggle.checked
                        Layout.fillWidth:true; Layout.fillHeight:needsSpace; Layout.leftMargin:28; Layout.rightMargin:28
                        Layout.preferredHeight: needsSpace ? -1 : Math.max(calendarArc.Layout.preferredHeight + 110, configContent.implicitHeight + 16)
                        Layout.topMargin:14; Layout.bottomMargin:12; spacing:26
                        ColumnLayout {
                            objectName:"taskInspector"; Layout.preferredWidth:Math.max(340, pages.width*.41-32)
                            Layout.minimumWidth:Layout.preferredWidth; Layout.maximumWidth:Layout.preferredWidth
                            Layout.fillHeight:true; spacing:12
                            ColumnLayout {
                                visible:!root.showMonitor; enabled:!preview.modelTesting; Layout.fillWidth:true; Layout.fillHeight:true; spacing:12
                                HorizonCalendar {
                                    id:calendarArc; objectName:"horizonCalendar"; Layout.fillWidth:true
                                    Layout.preferredHeight:Math.min(220, Math.max(150, root.height*.22))
                                    start:startDate.value; end:endDate.value
                                }
                                RowLayout {
                                    Layout.fillWidth: true; Layout.minimumHeight:32
                                    objectName: "dateSection"
                                    SmallLabel { text:"统计周期"; Layout.fillWidth:true }
                                    DatePreset { objectName: "recent7Days"; days: 7 }
                                    DatePreset { objectName: "recent30Days"; days: 30 }
                                }
                                RowLayout {
                                    objectName: "dateFields"
                                    Layout.fillWidth: true; spacing: 12
                                    DateField { onValueChanged: root.queueSave(); id: startDate; objectName: "startDate"; Layout.fillWidth: true; Layout.minimumWidth: 130; glassTexture: backdropTexture; glassScene: root.contentItem; reducedTransparency: root.reducedTransparency }
                                    Text { text: "至"; color: Pearl.muted; font.pixelSize: 12 }
                                    DateField { onValueChanged: root.queueSave(); id: endDate; objectName: "endDate"; Layout.fillWidth: true; Layout.minimumWidth: 130; glassTexture: backdropTexture; glassScene: root.contentItem; reducedTransparency: root.reducedTransparency }
                                }
                                Item { Layout.fillHeight:true }
                            }
                            ScrollView {
                                id: monitorScroll
                                objectName: "monitorScroll"
                                Layout.fillWidth:true; Layout.fillHeight:true; visible:root.showMonitor
                                contentWidth: availableWidth
                                ScrollBar.horizontal.policy: ScrollBar.AlwaysOff
                                clip: true
                                ColumnLayout {
                                    objectName: "monitorColumn"
                                    width: monitorScroll.availableWidth - 36
                                    x: 18; y: 16; spacing: 12
                                    RowLayout {
                                        Layout.fillWidth: true
                                        Icon { name: "activity"; width: 16; height: 16; tint: Pearl.accent }
                                        Text { text: "任务概览"; color: Pearl.ink; font.pixelSize: 13; font.weight: Font.DemiBold; Layout.fillWidth: true }
                                        Rectangle { width: 6; height: 6; radius: 3; color: preview.running ? Pearl.accent : Pearl.muted; opacity: pulse.running ? 0.6 : 1
                                            SequentialAnimation on opacity { id: pulse; running: preview.running && !root.reducedMotion; loops: Animation.Infinite; NumberAnimation { to: 0.3; duration: 700 } NumberAnimation { to: 1; duration: 700 } }
                                        }
                                    }
                                    ColumnLayout {
                                        spacing: 7; Layout.fillWidth: true
                                        Text { text: preview.state; color: Pearl.ink; font.pixelSize: 19; font.weight: Font.Medium; Layout.fillWidth: true; wrapMode: Text.Wrap }
                                        Text { text: preview.isDemo ? "离线演示 / 无网络请求" : "真实任务 / 本地报告"; font.pixelSize: 11; color: Pearl.muted }
                                    }
                                    Separator {}
                                    GridLayout {
                                        Layout.fillWidth: true; columns: 2; columnSpacing: 22; rowSpacing: 8
                                        SmallLabel { text: "已处理站点" }
                                        SmallLabel { text: "耗时" }
                                        Row {
                                                spacing: 4
                                            Text { text: preview.done; font.pixelSize: 27; color: Pearl.ink }
                                            Text { text: "/ " + (preview.running || preview.done > 0 ? preview.total : sources.selectedCount); font.pixelSize: 12; color: Pearl.muted; anchors.bottom: parent.bottom; anchors.bottomMargin: 4 }
                                        }
                                        Text { text: preview.elapsed; font.pixelSize: 24; color: Pearl.ink }
                                        SmallLabel { text: preview.isDemo ? "处理页面（演示）" : "处理页面"; font.pixelSize: 11; Layout.topMargin: 10 }
                                        SmallLabel { text: preview.isDemo ? "收录信息（演示）" : "收录信息"; font.pixelSize: 11; Layout.topMargin: 10 }
                                        Text { text: preview.pages; font.pixelSize: 23; color: Pearl.ink }
                                        Text { text: preview.hits; font.pixelSize: 23; color: Pearl.accent }
                                    }
                                    Rectangle {
                                        Layout.fillWidth: true; height: 3; color: Pearl.line; radius: 1.5
                                        Rectangle {
                                            height: 3; radius: 1.5; color: Pearl.accent
                                            width: parent.width * (preview.total ? preview.done / preview.total : 0)
                                            Behavior on width { NumberAnimation { duration: root.reducedMotion ? 0 : 250 } }
                                        }
                                    }
                                    Text {
                                        visible:root.technicalDetails; text: preview.stageSummary; color: Pearl.muted; font.pixelSize: 11
                                        Layout.fillWidth: true; Layout.minimumWidth: 0; Layout.preferredWidth: 0; wrapMode: Text.WrapAnywhere
                                    }
                                    Text {
                                        text: preview.coverageText; color: Pearl.ink; font.pixelSize: 12
                                        Layout.fillWidth: true; Layout.minimumWidth: 0; Layout.preferredWidth: 0; wrapMode: Text.WrapAnywhere
                                    }
                                    ColumnLayout {
                                        spacing: 9; Layout.fillWidth: true
                                        SmallLabel { text: preview.running ? "正在处理" : preview.done > 0 ? "最近任务" : "当前站点"; font.pixelSize: 11 }
                                        Text { text: preview.currentSite; color: Pearl.ink; font.pixelSize: 13; wrapMode: Text.Wrap; Layout.fillWidth: true }
                                        Text { text: preview.activeSources; visible: text.length > 0; color: Pearl.muted; font.pixelSize: 11; wrapMode: Text.Wrap; Layout.fillWidth: true }
                                        Text { text: preview.currentColumn; visible: root.technicalDetails && text.length > 0; color: Pearl.muted; font.pixelSize: 11; wrapMode: Text.WrapAnywhere; Layout.fillWidth: true; maximumLineCount: 2; elide: Text.ElideRight }
                                        RowLayout {
                                            spacing: 6
                                            Icon { name: preview.running ? "refresh-cw" : "circle-check"; width: 13; height: 13; tint: Pearl.muted }
                                            Text { text: preview.phase; color: Pearl.muted; font.pixelSize: 11 }
                                        }
                                    }
                                    Separator { Layout.topMargin: 2 }
                                    ColumnLayout {
                                        Layout.fillWidth: true; spacing: 14
                                        Repeater {
                                            model: ["栏目与列表", "详情提取", "分类与汇总", "PDF 报告"]
                                            RowLayout {
                                                required property string modelData; required property int index
                                                Layout.fillWidth: true; spacing: 11
                                                Rectangle {
                                                    width: 22; height: 22; radius: 11; color: Pearl.soft; border.width: 1; border.color: Pearl.muted
                                                    Text { anchors.centerIn: parent; text: (index + 1).toString().padStart(2, "0"); font.pixelSize: 9; color: Pearl.muted }
                                                }
                                                Text { text: modelData; font.pixelSize: 12; color: Pearl.muted; Layout.fillWidth: true }
                                                Icon { name: "chevron-right"; width: 12; height: 12; tint: Pearl.muted }
                                            }
                                        }
                                    }
                                    Item { Layout.preferredHeight: 12 }
                                }
                            }
                        }
                        Rectangle { Layout.fillHeight:true; width:1; color:Pearl.line }
                        ScrollView {
                            id:configScroll; objectName:"configScroll"; Layout.fillWidth:true; Layout.fillHeight:true
                            contentWidth:availableWidth; contentHeight:configContent.implicitHeight+16
                            ScrollBar.horizontal.policy:ScrollBar.AlwaysOff; clip:true
                            ColumnLayout {
                                id:configContent; objectName:"configContent"; width:configScroll.availableWidth-12; spacing:12
                                RowLayout {
                                    Layout.fillWidth:true
                                    Text { text:"采集安排"; font.family:root.serif; font.pixelSize:23; color:Pearl.ink; Layout.fillWidth:true }
                                    SmallLabel { text:preview.state; color:Pearl.active }
                                    AppButton { compact:true; tone:"ghost"; visible:preview.hasTask && !preview.running
                                        iconName:root.inspectLastTask ? "calendar-days" : "activity"
                                        hint:root.inspectLastTask ? "返回统计周历" : "查看最近任务概况"
                                        onClicked:root.inspectLastTask=!root.inspectLastTask }
                                }
                                SourcePicker {
                                    id:sitePicker; objectName:"sitePicker"; Layout.fillWidth:true; implicitHeight:48
                                    enabled:!preview.running; reducedTransparency:root.reducedTransparency
                                    glassTexture:backdropTexture; glassScene:root.contentItem
                                    onOpenedChanged:if(opened) root.drawer=""
                                }
                                DrawerHeading {
                                    objectName:"modelHeading"; label:"模型复判"; symbol:"sparkles"; fill:Pearl.warm
                                    summary:llmEnabled.checked ? (modelBox.currentText || "已启用") : "未启用"
                                    expanded:root.drawer==="model"; onClicked:root.toggleDrawer("model")
                                }
                                ColumnLayout {
                                    objectName:"modelDrawer"; visible:root.drawer==="model"; enabled:!preview.running && !preview.modelTesting
                                    Layout.fillWidth:true; spacing:10
                                    RowLayout {
                                        Layout.fillWidth:true
                                        SmallLabel { text:"启用模型复判"; Layout.fillWidth:true }
                                        Toggle { id:llmEnabled; objectName:"llmEnabled"; checked:true; Accessible.name:"启用模型复判"; onCheckedChanged:root.queueSave()
                                            ToolTip.visible:hovered; ToolTip.text:"只复核规则无法确定的候选文章，可能产生 API 费用" }
                                    }
                                    GridLayout {
                                        Layout.fillWidth: true; columns: 2; columnSpacing: 16; rowSpacing: 8
                                        uniformCellWidths: true
                                        enabled: !preview.modelsLoading
                                        SmallLabel { text: "接口地址" }
                                        SmallLabel { text: "API Key" }
                                        Field { id: apiUrl; objectName: "apiUrl"; Layout.fillWidth: true; placeholderText: "https://api.example.com/v1"; onTextChanged: root.queueSave() }
                                        Item {
                                            Layout.fillWidth: true; Layout.preferredHeight: 38
                                            Field {
                                                id: apiKey; objectName: "apiKey"; anchors.fill: parent
                                                readonly property bool keyHidden: echoMode === TextInput.Password
                                                placeholderText: "输入 API Key"; echoMode: revealKey.checked ? TextInput.Normal : TextInput.Password
                                                passwordCharacter: "●"; rightPadding: 37
                                                onTextChanged: root.queueSave()
                                            }
                                            AppButton {
                                                id: revealKey; objectName: "revealKey"
                                                anchors.right: parent.right; anchors.rightMargin: 3; anchors.verticalCenter: parent.verticalCenter
                                                width: 31; height: 30; compact: true; tone: "ghost"; checkable: true
                                                iconName: checked ? "eye-off" : "eye"; hint: checked ? "隐藏密钥" : "显示密钥"
                                            }
                                        }
                                    }
                                    RowLayout {
                                        Layout.fillWidth: true; spacing: 10
                                        ComboBox {
                                            id: modelBox; objectName: "modelBox"
                                            Layout.fillWidth: true; implicitHeight: 36
                                            model: preview.modelOptions
                                            enabled: !preview.modelsLoading
                                            leftPadding: 12; rightPadding: 30
                                            contentItem: Text { text: modelBox.displayText || "未获取模型"; verticalAlignment: Text.AlignVCenter; color: modelBox.currentIndex >= 0 ? Pearl.ink : Pearl.muted; font.pixelSize: 13; elide: Text.ElideRight }
                                            background: Rectangle { radius: 6; color: Pearl.soft; border.width: 1; border.color: modelBox.activeFocus ? Pearl.frame : Pearl.line }
                                            indicator: Icon { name: "chevrons-up-down"; x: modelBox.width - 25; y: 11; width: 14; height: 14 }
                                            delegate: ItemDelegate {
                                                required property string modelData
                                                required property int index
                                                width: modelBox.width - 8; height: 34
                                                highlighted: modelBox.highlightedIndex === index
                                                background: Rectangle { radius: 4; color: parent.hovered || parent.highlighted ? Pearl.soft : "transparent" }
                                                contentItem: Text { text: modelData; color: Pearl.ink; font.pixelSize: 13; verticalAlignment: Text.AlignVCenter; elide: Text.ElideRight }
                                                onClicked: { modelBox.currentIndex = index; root.desiredModel = modelData; modelBox.popup.close(); root.queueSave() }
                                            }
                                            onActivated: { root.desiredModel = currentText; root.queueSave() }
                                            popup: Popup {
                                                y: modelBox.height + 5; width: modelBox.width; padding: 4
                                                implicitHeight: Math.min(modelList.contentHeight, 280) + 8
                                                background: GlassSurface { texture: backdropTexture; scene: root.contentItem; radius: 10; frost: 8; whiteMix: 0.97; reducedTransparency: root.reducedTransparency }
                                                contentItem: ListView {
                                                    id: modelList; objectName: "modelList"
                                                    clip: true; implicitHeight: contentHeight
                                                    model: modelBox.popup.visible ? modelBox.delegateModel : null
                                                    currentIndex: modelBox.highlightedIndex
                                                    ScrollBar.vertical: ScrollBar { width: 7 }
                                                }
                                            }
                                        }
                                        AppButton {
                                            objectName: "fetchModels"; text: preview.modelsLoading ? "获取中…" : "获取模型"; iconName: "refresh-cw"; enabled: !preview.modelsLoading
                                            onClicked: { preview.saveConfig(root.currentOptions()); preview.fetchModels(apiUrl.text, apiKey.text, verifySsl.checked) }
                                        }
                                    }
                                    RowLayout {
                                        Layout.fillWidth: true
                                        AppButton {
                                            objectName: "testModel"; text: preview.modelTesting ? "测试中…" : "测试实际调用"
                                            iconName: "activity"
                                            enabled: !preview.isDemo && llmEnabled.checked && !preview.modelsLoading && !preview.modelTesting && modelBox.currentIndex >= 0
                                            onClicked: modelTestDialog.open()
                                        }
                                        Text {
                                            text: preview.modelTestResult; Layout.fillWidth: true; Layout.minimumWidth: 0; Layout.preferredWidth: 0; wrapMode: Text.WrapAnywhere
                                            font.pixelSize: 11; color: Pearl.muted; maximumLineCount: 3; elide: Text.ElideRight
                                            ToolTip.visible: testResultHover.hovered && text.length > 0
                                            ToolTip.text: text
                                            HoverHandler { id: testResultHover }
                                        }
                                    }
                                }
                                DrawerHeading {
                                    objectName:"advancedHeading"; label:"高级设置"; symbol:"sliders-horizontal"; fill:Pearl.neutral
                                    summary:(interval.value/10).toFixed(1)+" 秒 · 附件"+(attachments.checked ? "开启":"关闭")
                                    expanded:root.drawer==="advanced"; onClicked:root.toggleDrawer("advanced")
                                }
                                ColumnLayout {
                                    objectName:"advancedDrawer"; visible:root.drawer==="advanced"; Layout.fillWidth:true; spacing:12
                                    enabled:!preview.running && !preview.modelTesting
                                    RowLayout {
                                        Layout.fillWidth:true; Layout.minimumHeight:32;
                                        objectName: "runtimeSection"
                                        Item { Layout.fillWidth: true }
                                        SmallLabel { text: "请求间隔"; font.pixelSize: 11 }
                                        Rectangle {
                                            id: interval; objectName: "requestInterval"
                                            property int value: 5
                                            onValueChanged: root.queueSave()
                                            Layout.preferredWidth: 112; Layout.preferredHeight: 32
                                            radius: 4; color: Pearl.soft; border.width: 1; border.color: Pearl.line
                                            activeFocusOnTab: true
                                            Accessible.role: Accessible.SpinBox
                                            Accessible.name: "请求间隔 " + (value / 10).toFixed(1) + " 秒"
                                            Keys.onUpPressed: value = Math.min(600, value + 1)
                                            Keys.onDownPressed: value = Math.max(0, value - 1)
                                            AppButton { x: 1; y: 1; width: 28; height: 30; compact: true; tone: "ghost"; iconName: "minus"; hint: "减少请求间隔"; onClicked: interval.value = Math.max(0, interval.value - 1) }
                                            Text { anchors.centerIn: parent; text: (interval.value / 10).toFixed(1) + " s"; color: Pearl.ink; font.pixelSize: 11 }
                                            AppButton { anchors.right: parent.right; anchors.rightMargin: 1; y: 1; width: 28; height: 30; compact: true; tone: "ghost"; iconName: "plus"; hint: "增加请求间隔"; onClicked: interval.value = Math.min(600, interval.value + 1) }
                                        }
                                    }
                                    GridLayout {
                                        objectName: "runtimeOptions"
                                        Layout.fillWidth: true; columns: 2; columnSpacing: 28; rowSpacing: 8
                                        uniformCellWidths: true
                                        SettingPair { id: attachments; objectName: "attachments"; label: "下载附件"; checked: false; onCheckedChanged: root.queueSave() }
                                        SettingPair { id: verifySsl; objectName: "verifySsl"; label: "校验 SSL"; checked: true; onCheckedChanged: root.queueSave() }
                                        SettingPair { id: browserFallback; objectName: "browserFallback"; label: "浏览器兜底"; checked: true; onCheckedChanged: root.queueSave() }
                                        SettingPair { id: strictMode; objectName: "strictMode"; label: "严格筛选"; checked: true; onCheckedChanged: root.queueSave() }
                                    }
                                    CheckControl { id: ruleFallback; objectName: "ruleFallback"; text: "未启用模型时，允许规则收录模糊候选"; checked: false; onCheckedChanged: root.queueSave() }
                                    RowLayout {
                                        Layout.topMargin: 0
                                        Layout.fillWidth: true; spacing: 7
                                        Icon { name: "folder-open"; width: 14; height: 14; tint: Pearl.muted }
                                        Text { text: preview.outputPath; font.pixelSize: 11; color: Pearl.muted; elide: Text.ElideMiddle; Layout.fillWidth: true }
                                        AppButton { text: "更改"; iconName: "folder-open"; tone: "ghost"; compact: true; hint: "选择输出目录"; onClicked: preview.chooseOutput() }
                                    }
                                }
                                RowLayout {
                                    Layout.fillWidth:true; spacing:8
                                    SmallLabel { text:"最近一期" }
                                    AppButton { objectName:"latestReport"; compact:true; tone:"ghost"; enabled:!!preview.latestReport.path
                                        iconName:enabled ? "external-link" : ""
                                        text:!enabled ? "暂无周报" : preview.latestReport.start===preview.latestReport.end
                                             ? preview.latestReport.start : preview.latestReport.start+" 至 "+preview.latestReport.end
                                        hint:enabled ? "打开周报 PDF" : ""; onClicked:preview.openFile(preview.latestReport.path) }
                                    Item { Layout.fillWidth:true }
                                }
                                AppButton { objectName:"taskCoverage"; compact:true; text:"任务详情与恢复"; iconName:"activity"
                                    visible:preview.hasTask; onClicked:coverageDialog.open() }
                            }
                        }
                    }
                    Separator {}
                    Rectangle {
                        Layout.fillWidth: true
                        Layout.preferredHeight: logToggle.checked ? Math.max(180, Math.min(240, root.height * 0.26)) : 44
                        Layout.fillHeight: logToggle.checked && !root.showMonitor && root.drawer === ""
                        color: Pearl.surface
                        Behavior on Layout.preferredHeight { NumberAnimation { duration: root.reducedMotion ? 0 : 160; easing.type: Easing.OutCubic } }
                        ColumnLayout {
                            anchors.fill: parent; spacing: 0
                            RowLayout {
                                Layout.fillWidth: true; Layout.preferredHeight: 44; Layout.leftMargin: 28; Layout.rightMargin: 18
                                Text { text:root.technicalDetails ? "技术明细" : "任务动态"; color:Pearl.ink; font.family:root.serif; font.pixelSize:18 }
                                Item { Layout.fillWidth: true }
                                CheckControl {
                                    visible: root.technicalDetails && logToggle.checked
                                    text: "跟随最新"; checked: logs.followTail
                                    onClicked: { logs.followTail = !logs.followTail; if (logs.followTail) logs.positionViewAtEnd() }
                                }
                                Field {
                                    id: logSearch; objectName: "logSearch"
                                    visible: root.technicalDetails && logToggle.checked
                                    Layout.preferredWidth: 160; implicitHeight: 26; font.pixelSize: 11
                                    placeholderText: "筛选日志"; onTextChanged: logModel.query = text
                                }
                                AppButton { visible:root.technicalDetails && logToggle.checked; iconName: "x"; compact: true; tone: "ghost"; hint: "清空技术明细"; onClicked: preview.clearLogs() }
                                AppButton { objectName:"activityMode"; compact:true; tone:"ghost"
                                    text:root.technicalDetails ? "返回任务动态" : "技术明细"
                                    iconName:root.technicalDetails ? "chevron-left" : "chevron-right"
                                    onClicked:{logToggle.checked=true;root.technicalDetails=!root.technicalDetails} }
                                AppButton { id: logToggle; iconName: "chevron-down"; compact: true; tone: "ghost"; hint: checked ? "收起日志" : "展开日志"; checkable: true; checked: true; rotation: checked ? 0 : 180 }
                            }
                            ActivityFeed {
                                visible:logToggle.checked && !root.technicalDetails
                                Layout.fillWidth:true; Layout.fillHeight:true; Layout.leftMargin:28; Layout.rightMargin:22; Layout.bottomMargin:7
                                onActionRequested:function(action) {
                                    if(action==="report" && preview.lastPdf) preview.openFile(preview.lastPdf)
                                    else if(action==="coverage" && preview.hasTask) coverageDialog.open()
                                    else root.technicalDetails=true
                                }
                            }
                            Rectangle {
                                Layout.fillWidth: true; Layout.preferredHeight: 23
                                visible: root.technicalDetails && logToggle.checked; color: Pearl.neutral
                                Text { x: 20; anchors.verticalCenter: parent.verticalCenter; text: "时间"; font.pixelSize: 10; color: Pearl.muted }
                                Text { x: 102; anchors.verticalCenter: parent.verticalCenter; text: "级别"; font.pixelSize: 10; color: Pearl.muted }
                                Text { x: 170; anchors.verticalCenter: parent.verticalCenter; text: "消息"; font.pixelSize: 10; color: Pearl.muted }
                            }
                            ListView {
                                id: logs; objectName: "logList"
                                property bool followTail: true
                                Layout.fillWidth: true; Layout.fillHeight: true; Layout.leftMargin: 20; Layout.rightMargin: 18; Layout.bottomMargin: 6
                                visible: root.technicalDetails && logToggle.checked
                                clip: true; model: logModel; spacing: 0
                                boundsBehavior: Flickable.StopAtBounds
                                ScrollBar.vertical: ScrollBar {
                                    id: logScrollbar
                                    width: 7
                                    onPressedChanged: { if (!pressed) logs.followTail = logs.atYEnd }
                                }
                                onMovementStarted: followTail = false
                                onMovementEnded: followTail = atYEnd
                                WheelHandler {
                                    target: null; blocking: false
                                    onWheel: function(event) {
                                        if (event.angleDelta.y > 0 || event.pixelDelta.y > 0) logs.followTail = false
                                        else Qt.callLater(function() { if (logs.atYEnd) logs.followTail = true })
                                    }
                                }
                                delegate: LogRow {
                                    width: logs.width - 12
                                }
                                AppButton {
                                    anchors.right: parent.right; anchors.rightMargin: 14; anchors.bottom: parent.bottom
                                    iconName: "arrow-down"; compact: true; hint: "回到最新日志"; visible: !logs.followTail
                                    onClicked: { logs.followTail = true; logs.positionViewAtEnd() }
                                }
                            }
                        }
                    }
                }

                ColumnLayout {
                    id: sitesPage
                    anchors { fill: parent; margins: 30 }
                    opacity: root.page === 1 ? 1 : 0
                    visible: opacity > 0
                    enabled: root.page === 1
                    Behavior on opacity { NumberAnimation { duration: root.reducedMotion ? 0 : 170 } }
                    spacing: 18
                    RowLayout {
                        Layout.fillWidth: true
                        ColumnLayout {
                            spacing: 6
                            Text { text: sources.total + " 个采集站点"; color: Pearl.ink; font.pixelSize: 17; font.weight: Font.DemiBold }
                            SmallLabel { text: Object.keys(sources.regionCounts).length + " 个地区 · " + sources.departments + " 类部门" }
                        }
                        Item { Layout.fillWidth: true }
                        TabBar {
                            id: siteMode; objectName: "siteViewMode"
                            Layout.preferredWidth: 144
                            implicitHeight: 36
                            Layout.minimumHeight: 36; Layout.maximumHeight: 36
                            padding: 3; spacing: 2
                            topInset: 0; bottomInset: 0; leftInset: 0; rightInset: 0
                            currentIndex: root.siteMapMode ? 0 : 1
                            onCurrentIndexChanged: root.siteMapMode = currentIndex === 0
                            background: Rectangle { radius: 6; color: Pearl.soft }
                            SegmentTab { objectName: "mapViewTab"; text: "地图"; height: siteMode.availableHeight }
                            SegmentTab { objectName: "listViewTab"; text: "列表"; height: siteMode.availableHeight }
                        }
                        Field { id: manageSearch; objectName: "manageSearch"; Layout.preferredWidth: 235; placeholderText: "搜索站点或地区"; onTextChanged: manageFilter.query = text }
                        AppButton { objectName: "checkCatalogueUpdates"; visible: !!root.updates; iconName: "refresh-cw"; compact: true
                            hint: "检查站点配置更新"; onClicked: { updateDialog.open(); root.updates.check() } }
                    }
                    RowLayout {
                        Layout.fillWidth: true
                        CheckControl { text: "全部站点"; checked: sources.selectedCount === sources.total; partial: sources.selectedCount > 0 && sources.selectedCount < sources.total; enabled: !preview.running; onClicked: sources.selectAll(sources.selectedCount !== sources.total) }
                        Item { Layout.fillWidth: true }
                        SmallLabel { text: "已选择 " + sources.selectedCount + " / " + sources.total }
                    }
                    Separator {}
                    SiteMapView {
                        Layout.fillWidth: true; Layout.fillHeight: true
                        visible: root.siteMapMode; reducedMotion: root.reducedMotion
                        query: manageSearch.text
                    }
                    RowLayout {
                        visible: !root.siteMapMode
                        Layout.fillWidth: true; Layout.leftMargin: 44; Layout.rightMargin: 8; spacing: 12
                        SmallLabel { text: "站点名称"; Layout.fillWidth: true }
                        SmallLabel { text: "地区"; Layout.preferredWidth: 42 }
                        SmallLabel { text: "栏目数"; Layout.preferredWidth: 54 }
                        SmallLabel { text: "配置状态"; Layout.preferredWidth: 92 }
                        SmallLabel { text: "操作"; Layout.preferredWidth: 32 }
                    }
                    ListView {
                        id: manageList; objectName: "manageList"
                        visible: !root.siteMapMode
                        Layout.fillWidth: true; Layout.fillHeight: true
                        model: manageFilter; clip: true; spacing: 0
                        ScrollBar.vertical: ScrollBar { width: 8 }
                        delegate: Item {
                            required property int siteId; required property string siteName; required property string region
                            required property int channels; required property bool selected; required property string siteUrl
                            width: manageList.width - 8; height: 64
                            Rectangle { anchors.fill: parent; color: manageHover.hovered ? Pearl.soft : "transparent"; radius: 5 }
                            HoverHandler { id: manageHover }
                            RowLayout {
                                anchors.fill: parent; spacing: 12
                                CheckControl { Layout.preferredWidth: 24; Layout.leftMargin: 8; checked: selected; enabled: !preview.running; onClicked: sources.toggle(siteId) }
                                ColumnLayout {
                                    Layout.fillWidth: true; spacing: 4
                                    Text { text: siteName; color: Pearl.ink; font.pixelSize: 13; Layout.fillWidth: true; elide: Text.ElideRight }
                                    Text { text: siteUrl; color: Pearl.muted; font.pixelSize: 10; Layout.fillWidth: true; elide: Text.ElideRight }
                                }
                                SmallLabel { text: region; Layout.preferredWidth: 42 }
                                SmallLabel { text: channels; Layout.preferredWidth: 54 }
                                SmallLabel { text: "配置已载入"; color: Pearl.muted; Layout.preferredWidth: 92 }
                                RowLayout {
                                    Layout.preferredWidth: 32
                                    AppButton { iconName: "arrow-up-right"; tone: "ghost"; compact: true; hint: "在浏览器打开网站"; onClicked: preview.openSite(siteUrl) }
                                }
                            }
                            Rectangle { anchors.bottom: parent.bottom; width: parent.width; height: 1; color: Pearl.soft }
                        }
                        Text { anchors.centerIn: parent; visible: manageList.count === 0; text: "没有匹配的站点"; color: Pearl.muted; font.pixelSize: 14 }
                    }
                }

                ColumnLayout {
                    anchors { fill: parent; margins: 30 }
                    opacity: root.page === 2 ? 1 : 0
                    visible: opacity > 0
                    enabled: root.page === 2
                    Behavior on opacity { NumberAnimation { duration: root.reducedMotion ? 0 : 170 } }
                    spacing: 20
                    RowLayout {
                        Layout.fillWidth: true
                        Text { text: "本地 PDF 报告"; color: Pearl.ink; font.pixelSize: 16; font.weight: Font.DemiBold; Layout.fillWidth: true }
                        AppButton { iconName: "refresh-cw"; hint: "刷新报告列表"; tone: "ghost"; onClicked: preview.refreshReports() }
                        AppButton { text: "打开输出目录"; iconName: "folder-open"; onClicked: preview.openFile(preview.outputPath) }
                    }
                    Separator {}
                    ListView {
                        id: reportList
                        Layout.fillWidth: true; Layout.fillHeight: true
                        model: reportModel; spacing: 12; clip: true
                        ScrollBar.vertical: ScrollBar { width: 8 }
                        delegate: Rectangle {
                            required property string reportName; required property string reportPath
                            required property string reportDate; required property string reportSize
                            width: reportList.width; height: 78; radius: 6; color: Pearl.soft; border.width: 1; border.color: Pearl.line
                            RowLayout {
                                anchors { fill: parent; leftMargin: 20; rightMargin: 16 }
                                spacing: 18
                                Icon { name: "file-text"; tint: Pearl.accent; width: 26; height: 26 }
                                ColumnLayout {
                                    Layout.fillWidth: true; spacing: 7
                                    Text { text: reportName; color: Pearl.ink; font.pixelSize: 14; Layout.fillWidth: true; elide: Text.ElideRight }
                                    SmallLabel { text: reportDate + "  ·  " + reportSize; font.pixelSize: 11 }
                                }
                                AppButton { iconName: "external-link"; text: "打开 PDF"; onClicked: preview.openFile(reportPath) }
                            }
                        }
                        ColumnLayout {
                            anchors.centerIn: parent; spacing: 15; visible: reportList.count === 0
                            Icon { name: "file-text"; width: 42; height: 42; tint: Pearl.muted; Layout.alignment: Qt.AlignHCenter }
                            Text { text: "暂无本地报告"; font.pixelSize: 16; color: Pearl.ink; Layout.alignment: Qt.AlignHCenter }
                        }
                    }
                }

                ColumnLayout {
                    anchors { fill: parent; margins: 30 }
                    opacity: root.page === 3 ? 1 : 0
                    visible: opacity > 0
                    enabled: root.page === 3
                    Behavior on opacity { NumberAnimation { duration: root.reducedMotion ? 0 : 170 } }
                    spacing: 22
                    Text { text: "外观与交互"; color: Pearl.ink; font.pixelSize: 16; font.weight: Font.DemiBold }
                    RowLayout {
                        visible: !!root.updates; Layout.fillWidth: true
                        SmallLabel { text: "软件与站点配置"; Layout.fillWidth: true }
                        AppButton { objectName: "checkUpdates"; iconName: "refresh-cw"; compact: true; hint: "检查更新"
                            onClicked: { updateDialog.open(); root.updates.check() } }
                    }
                    Separator {}
                    RowLayout {
                        Layout.fillWidth: true; Layout.preferredHeight: 46
                        SmallLabel { text: "外观"; Layout.fillWidth: true; font.pixelSize: 13 }
                        Text { text: "珍珠灰 · 雾玫瑰"; color: Pearl.ink; font.pixelSize: 13 }
                        Rectangle { width: 22; height: 22; radius: 5; color: Pearl.accent }
                    }
                    Separator {}
                    RowLayout {
                        Layout.fillWidth: true; Layout.preferredHeight: 46
                        SmallLabel { text: "减少动态效果"; Layout.fillWidth: true; font.pixelSize: 13 }
                        Toggle { objectName: "reducedMotion"; checked: root.reducedMotion; onClicked: root.reducedMotion = checked; Accessible.name: "减少动态效果" }
                    }
                    Separator {}
                    RowLayout {
                        Layout.fillWidth: true; Layout.preferredHeight: 46
                        SmallLabel { text: "启动动画"; Layout.fillWidth: true; font.pixelSize: 13 }
                        AppButton { text: "重新播放"; iconName: "rotate-ccw"; enabled:!preview.running; onClicked: root.replayIntro() }
                    }
                    Separator {}
                    RowLayout {
                        Layout.fillWidth: true; Layout.preferredHeight: 46
                        SmallLabel { text: "运行模式"; Layout.fillWidth: true; font.pixelSize: 13 }
                        Text { text: preview.isDemo ? "离线界面预览" : "真实采集"; color: Pearl.accent; font.pixelSize: 13 }
                    }
                    Separator {}
                    RowLayout {
                        Layout.fillWidth: true; Layout.preferredHeight: 46
                        SmallLabel { text: "减少透明效果"; Layout.fillWidth: true; font.pixelSize: 13 }
                        Toggle { objectName: "reducedTransparency"; checked: root.reducedTransparency; onClicked: root.reducedTransparency = checked; Accessible.name: "减少透明效果" }
                    }
                    Item { Layout.fillHeight: true }
                    Text { text: "Policy Weekly · " + preview.buildLabel; color: Pearl.muted; font.pixelSize: 11 }
                }
            }
            Separator {}
            RowLayout {
                Layout.fillWidth: true; Layout.preferredHeight: 30; Layout.leftMargin: 28; Layout.rightMargin: 26
                spacing: 7
                Icon { name: "shield-check"; width: 12; height: 12; tint: Pearl.muted }
                Text { text: preview.isDemo ? "离线预览" : "本地运行"; color: Pearl.muted; font.pixelSize: 10 }
                Rectangle { width: 1; height: 9; color: Pearl.soft; Layout.leftMargin: 5; Layout.rightMargin: 5 }
                Text { text: sources.selectedCount + " 个站点已选"; color: Pearl.muted; font.pixelSize: 10 }
                Item { Layout.fillWidth: true }
                Text { text: "PDF"; color: Pearl.muted; font.pixelSize: 10 }
                Text { text: "·"; color: Pearl.muted; font.pixelSize: 11 }
                Text { text: "本地输出"; color: Pearl.muted; font.pixelSize: 10 }
            }
        }
    }

    Dialog {
        id: modelTestDialog; objectName: "modelTestDialog"
        anchors.centerIn: parent; width: 440; modal: true
        title: "测试实际模型调用"
        standardButtons: Dialog.Ok | Dialog.Cancel
        contentItem: Text {
            text: "将向当前服务发送一段内置虚构样例，不上传采集文章。测试会产生少量 API 用量；接口适配可能发送多次请求，最长等待 180 秒。"
            color: Pearl.ink; wrapMode: Text.Wrap; font.pixelSize: 13
        }
        onAccepted: preview.testModel(root.currentOptions())
    }

    Dialog {
        id: coverageDialog; objectName: "coverageDialog"
        anchors.centerIn: parent; width: Math.min(root.width - 80, 850); height: Math.min(root.height - 80, 620)
        modal: true; title: "最近任务 · 采集覆盖与恢复"
        footer: Item {
            implicitHeight: 52
            AppButton { text: "关闭"; iconName: "x"; anchors.right: parent.right; anchors.rightMargin: 16; anchors.verticalCenter: parent.verticalCenter; onClicked: coverageDialog.close() }
        }
        property string expandedSource: ""
        contentItem: ColumnLayout {
            spacing: 12
            Text { text: preview.coverageText; Layout.fillWidth: true; wrapMode: Text.Wrap; color: Pearl.ink }
            RowLayout {
                AppButton {
                    objectName: "resumeTask"; text: "继续／补采失败项"; iconName: "refresh-cw"
                    enabled: !preview.running && !preview.modelTesting && !preview.modelsLoading && preview.hasTask
                    onClicked: { preview.resumeTask("resume", root.currentOptions()); coverageDialog.close() }
                }
                AppButton {
                    objectName: "retryModelFailures"; text: "仅重试模型"; iconName: "sparkles"
                    enabled: !preview.running && !preview.modelTesting && !preview.modelsLoading && preview.hasTask
                    onClicked: { preview.resumeTask("llm", root.currentOptions()); coverageDialog.close() }
                }
                AppButton {
                    objectName: "freshCheck"; text: "重新核验所选站点"; iconName: "refresh-cw"
                    hint: "按当前日期和站点新建任务，不复用网页或模型缓存；可能产生模型费用"
                    enabled: !preview.isDemo && !preview.running && !preview.modelTesting && !preview.modelsLoading && sources.selectedCount > 0
                    onClicked: freshDialog.open()
                }
            }
            ListView {
                objectName: "coverageList"; Layout.fillWidth: true; Layout.fillHeight: true; clip: true
                model: preview.coverageSources; spacing: 1
                ScrollBar.vertical: ScrollBar {}
                delegate: Column {
                    required property var modelData
                    width: ListView.view.width; spacing: 6
                    ItemDelegate {
                        id: coverageSourceRow
                        width: parent.width; height: 44
                        text: modelData.name + " · " + modelData.label + " · " + modelData.pages + " 页 / " + modelData.failed_pages + " 页待核查"
                        onClicked: coverageDialog.expandedSource = coverageDialog.expandedSource === modelData.name ? "" : modelData.name
                        contentItem: RowLayout {
                            Text { text: coverageSourceRow.text; Layout.fillWidth: true; font.pixelSize: 12; color: Pearl.ink; wrapMode: Text.Wrap }
                            Icon { name: "chevron-right"; width: 16; height: 16; rotation: coverageDialog.expandedSource === modelData.name ? 90 : 0; tint: Pearl.muted }
                        }
                    }
                    Text {
                        width: parent.width - 20; x: 10
                        visible: coverageDialog.expandedSource === modelData.name
                        text: "收录 " + modelData.counts.included + " · 排除 " + modelData.counts.excluded + " · 日期范围外 " + modelData.counts.out_of_range + " · 待复判 " + modelData.counts.llm_failed + " · 详情失败 " + modelData.counts.detail_failed
                        color: Pearl.muted; font.pixelSize: 12; wrapMode: Text.Wrap
                    }
                    Repeater {
                        model: coverageDialog.expandedSource === modelData.name ? modelData.details : []
                        delegate: Text {
                            required property var modelData
                            width: parent.width - 20; x: 10; font.pixelSize: 11; color: Pearl.muted; wrapMode: Text.WrapAnywhere
                            text: (modelData.column || "列表页") + " · " + (modelData.outcome || {complete:"已检查",failed:"失败",empty:"待核查",pending:"未完成"}[modelData.status] || modelData.status) + "\n" + modelData.url + (modelData.stop ? "\n" + modelData.stop : "") + (modelData.reason && modelData.reason !== modelData.outcome ? "\n" + modelData.reason : "")
                        }
                    }
                    Repeater {
                        model: coverageDialog.expandedSource === modelData.name ? modelData.issues : []
                        delegate: Text {
                            required property var modelData
                            width: parent.width - 20; x: 10; font.pixelSize: 11; color: "#96612e"; wrapMode: Text.WrapAnywhere
                            text: (modelData.title || "待处理文章") + " · " + ({llm_failed:"待复判",detail_failed:"详情失败",pending:"未完成"}[modelData.status] || modelData.status) + "\n" + modelData.url + "\n" + modelData.reason
                        }
                    }
                    Rectangle { width: parent.width; height: 1; color: Pearl.line }
                }
            }
        }
    }

    Dialog {
        id: exitDialog; objectName: "exitDialog"
        anchors.centerIn: parent; width: 360; modal: true
        title: "任务正在运行"
        standardButtons: Dialog.Yes | Dialog.No
        contentItem: Text { text: "退出会停止当前采集任务。确定退出吗？"; color: Pearl.ink; font.pixelSize: 13; wrapMode: Text.Wrap }
        onAccepted: { preview.saveConfig(root.currentOptions()); preview.requestExit() }
    }

    Dialog {
        id: freshDialog; objectName: "freshDialog"; anchors.centerIn: parent; modal: true; width: 420
        title: "重新核验所选站点？"; standardButtons: Dialog.Ok | Dialog.Cancel
        contentItem: Text {
            text: "使用工作台当前日期和站点新建任务，不覆盖旧报告。不复用网页或模型缓存；启用模型时可能产生新的 API 用量。"
            wrapMode: Text.Wrap; color: Pearl.ink
        }
        onAccepted: { coverageDialog.close(); preview.start(startDate.value, endDate.value, Object.assign({}, root.currentOptions(), {fresh_check:true})) }
    }

    Dialog {
        id: updateDialog; objectName: "updateDialog"; title: "软件与站点配置更新"; modal: true
        anchors.centerIn: parent; width: Math.min(root.width - 80, 490)
        standardButtons: Dialog.Close
        contentItem: ColumnLayout {
            spacing: 12
            Label { Layout.fillWidth: true; textFormat: Text.PlainText; wrapMode: Text.Wrap
                text: root.updates ? root.updates.status : "" }
            Repeater {
                model: root.updates ? root.updates.items : []
                delegate: ColumnLayout {
                    required property var modelData
                    Layout.fillWidth: true
                    RowLayout {
                        Layout.fillWidth: true
                        Label { text: modelData.title + " · " + modelData.size; Layout.fillWidth: true; wrapMode: Text.Wrap }
                        AppButton { objectName: "downloadUpdate_" + modelData.kind; text: "下载"; iconName: "arrow-down"
                            enabled: root.updates && !root.updates.busy && !root.updates.prepared
                            onClicked: root.updates.download(modelData.kind) }
                    }
                    Label { text: modelData.note; textFormat: Text.PlainText; Layout.fillWidth: true
                        wrapMode: Text.Wrap; maximumLineCount: 4; elide: Text.ElideRight; font.pixelSize: 12 }
                }
            }
            RowLayout {
                visible: !!root.updates && !!root.updates.prepared
                AppButton { objectName: "applyUpdate"; text: root.updates && root.updates.prepared === "app" ? "安装并重启" : "应用站点配置"; tone: "primary"
                    enabled: !!root.updates && !root.updates.busy && !preview.running && !preview.modelTesting && !preview.modelsLoading
                    onClicked: root.updates.apply() }
                AppButton { text: "放弃本次下载"; enabled: !!root.updates && !root.updates.busy; onClicked: root.updates.discard() }
            }
        }
    }

    StartupScene {
        id: startup; objectName: "startupScene"
        anchors.fill: parent
        visible: root.booting; z: 10
        progress: root.introProgress
        brandTarget:brandTitle
        onSkipRequested: root.finishIntro()
    }
    Rectangle {
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.bottom: parent.bottom; anchors.bottomMargin: 48
        width: Math.min(toastLabel.implicitWidth + 40, root.width - 80)
        height: 44; radius: 7
        color: Pearl.soft; border.width: 1; border.color: Pearl.muted
        opacity: root.toastShown ? 1 : 0
        visible: opacity > 0
        z: 20
        Behavior on opacity { NumberAnimation { duration: 160 } }
        Text { id: toastLabel; anchors.centerIn: parent; text: root.toastText; font.pixelSize: 12; color: Pearl.ink; width: Math.min(implicitWidth, parent.width - 30); elide: Text.ElideRight }
    }
}
