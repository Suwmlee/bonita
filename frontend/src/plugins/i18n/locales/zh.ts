export default {
  app: {
    title: "Bonita",
    description: "Bonita 前端应用",
  },
  navitems: {
    dashboard: "仪表盘",
    records: "记录",
    tasks: "任务配置",
    scraping: "刮削配置",
    metadata: "元数据",
    tools: "工具",
    serviceSettings: "服务设置",
    userSettings: "用户设置",
  },
  common: {
    save: "保存",
    cancel: "取消",
    confirm: "确认",
    delete: "删除",
    edit: "编辑",
    add: "添加",
    search: "搜索",
    back: "返回",
    submit: "提交",
    loading: "加载中...",
    noData: "暂无数据",
    success: "成功",
    failed: "失败",
    unknown: "未知",
    yes: "是",
    no: "否",
    all: "全部",
    more: "更多",
    refresh: "刷新",
    next: "下一步",
    prev: "上一步",
    optional: "可选",
    required: "必填",
    saveChanges: "保存更改",
    reset: "重置",
    editTitle: "编辑",
    addTitle: "添加",
    actions: "操作",
  },
  auth: {
    login: "登录",
    logout: "退出登录",
    register: "注册",
    username: "用户名",
    password: "密码",
    email: "电子邮箱",
    forgotPassword: "忘记密码",
    rememberMe: "记住我",
    loginSuccess: "登录成功",
    loginFailed: "登录失败",
    invalidCredentials: "用户名或密码错误",
    welcomeMessage: "请登录您的账户，开始冒险之旅",
    enterEmail: "请输入邮箱",
    enterPassword: "请输入密码",
    changePassword: "修改密码",
    currentPassword: "当前密码",
    newPassword: "新密码",
    confirmPassword: "确认新密码",
    passwordRequirements: "密码要求：",
    passwordMinLength: "至少8个字符 - 越长越好",
  },
  menu: {
    home: "首页",
    dashboard: "仪表盘",
    settings: "设置",
    profile: "个人资料",
    users: "用户管理",
    roles: "角色管理",
    permissions: "权限管理",
  },
  language: {
    zh: "中文",
    en: "英文",
    switchSuccess: "语言切换成功",
  },
  time: {
    today: "今天",
    yesterday: "昨天",
    tomorrow: "明天",
    day: "天",
    week: "周",
    month: "月",
    year: "年",
    hour: "小时",
    minute: "分钟",
    second: "秒",
  },
  errors: {
    networkError: "网络错误，请检查您的网络连接",
    serverError: "服务器错误，请稍后再试",
    notFound: "未找到资源",
    forbidden: "无权访问",
    unauthorized: "未授权访问",
    timeout: "请求超时",
    unknown: "未知错误",
  },
  validation: {
    required: "{field}不能为空",
    minLength: "{field}长度不能少于{length}个字符",
    maxLength: "{field}长度不能超过{length}个字符",
    email: "请输入有效的电子邮箱地址",
    url: "请输入有效的URL",
    numeric: "请输入数字",
    alpha: "只能输入字母",
    alphaNum: "只能输入字母和数字",
  },
  pages: {
    dashboard: {
      title: "仪表盘",
      activeTasks: "活动任务",
      noRunningTasks: "当前没有运行中的任务",
      taskName: "任务名称",
      status: "状态",
      source: "来源",
      destination: "目标",
      unknownTask: "未知任务",
      running: "运行中",
    },
    task: {
      title: "任务",
      addTask: "添加任务",
      runNow: "立即执行",
      running: "运行中",
      delete: "删除",
      directoryHint: "输入要针对运行的目录，留空则运行整个任务",
    },
    metadata: {
      title: "元数据",
      addNew: "添加新元数据",
      search: "搜索编号或演员...",
      number: "编号",
      metadataTitle: "标题",
      actor: "演员",
      tag: "标签",
      update: "更新时间",
      cover: "封面",
      noResults: "未找到元数据。请调整搜索或添加新元数据。",
      itemsPerPage: "每页显示",
      totalItems: "总计 {count} 条记录",
      editMetadata: "编辑元数据",
      addMetadata: "添加元数据",
    },
    tools: {
      title: "工具",
      importNfo: {
        title: "从NFO导入元数据",
        subtitle: "在此导入NFO文件中的电影元数据信息",
        folder: "NFO文件夹",
        folderPlaceholder: "例如: D:\\Movies\\NFO",
        importMethod: "导入方式",
        ignoreExisting: "忽略已有数据",
        forceUpdate: "强制更新",
        startImport: "开始导入",
        folderRequired: "请输入文件夹路径",
      },
    },
    serviceSettings: {
      title: "服务配置",
      proxy: {
        title: "代理设置",
        subtitle: "此处配置的代理将用于应用程序的网络请求",
        http: "HTTP 代理",
        https: "HTTPS 代理",
        httpsPlaceholder: "例如: http://127.0.0.1:7890",
        enable: "启用代理",
        save: "保存设置",
      },
      emby: {
        title: "Emby API 设置",
        subtitle: "配置Emby服务器API连接参数",
        server: "Emby 服务器",
        serverPlaceholder: "例如: http://emby.example.com:8096",
        apiKey: "API Key",
        apiKeyPlaceholder: "Emby API Key",
        save: "保存设置",
        test: "测试连接",
        saveSuccess: "Emby设置已成功保存",
        saveError: "保存Emby设置失败，请稍后重试",
        testError: "测试连接失败，请检查您的设置和网络",
        connectionSuccess: "连接成功！",
        connectionError: "连接失败！",
        enable: "启用Emby集成",
      },
      jellyfin: {
        title: "Jellyfin API 设置",
        subtitle: "配置Jellyfin服务器API连接参数",
        server: "Jellyfin 服务器",
        serverPlaceholder: "例如: http://jellyfin.example.com:8096",
        apiKey: "API Key",
        apiKeyPlaceholder: "Jellyfin API Key",
        save: "保存设置",
        test: "测试连接",
        saveSuccess: "Jellyfin设置已成功保存",
        saveError: "保存Jellyfin设置失败，请稍后重试",
        testError: "测试连接失败，请检查您的设置和网络",
        connectionSuccess: "连接成功！",
        connectionError: "连接失败！",
        enable: "启用Jellyfin集成",
      },
    },
    userSettings: {
      title: "用户设置",
      tabs: {
        security: "安全",
      },
    },
    records: {
      title: "记录",
      edit: "编辑记录",
      search: "文件名搜索",
      filterTaskId: "过滤任务ID",
      deleteSelected: "删除选中项",
      nameFilter: "文件名",
      taskIdFilter: "任务ID",
      clearFilters: "清除所有筛选条件",
      itemsPerPage: "每页显示",
      totalRecords: "总计 {count} 条记录",
      name: "名称",
      path: "路径",
      destPath: "目标路径",
      season: "季",
      episode: "集",
      number: "编号",
      tag: "标签",
      updateTime: "更新时间",
      deadTime: "截止时间",
      actions: "操作",
      deleteDialog: {
        title: "确认删除",
        message: "您确定要删除选中的 {count} 条记录吗？此操作无法撤销。",
        forceDelete: "强制删除（忽略锁定状态）",
        cancel: "取消",
        confirm: "删除",
      },
    },
    scraping: {
      title: "刮削配置",
      edit: "编辑配置",
      add: "添加配置",
    },
  },
  components: {
    metadata: {
      dialog: {
        editTitle: "编辑元数据",
        addTitle: "添加元数据",
      },
      form: {
        number: "编号",
        title: "标题",
        studio: "制片商",
        release: "发行日期",
        year: "年份",
        runtime: "片长",
        genre: "类型",
        rating: "评分",
        language: "语言",
        country: "国家",
        outline: "简介",
        director: "导演",
        actor: "演员",
        actorPhoto: "演员照片",
        cover: "封面",
        coverSmall: "小封面",
        extraFanart: "额外图片",
        trailer: "预告片",
        tag: "标签",
        label: "标签",
        series: "系列",
        userRating: "用户评分",
        userVotes: "用户投票",
        detailUrl: "详情链接",
        site: "网站",
        required: "必填",
        validation: {
          numberRequired: "编号不能为空",
          titleRequired: "标题不能为空",
        },
        uploadCover: "上传封面",
        selectImage: "选择图片",
        imageTypeError: "请选择图片文件（JPEG、PNG等）。",
        uploadError: "上传失败，请重试。",
        uploadSuccess: "图片上传成功，但无法确定路径。请查看控制台了解详情。",
        save: "保存",
        cancel: "取消",
      },
    },
    common: {
      confirmation: {
        title: "确认",
        cancelText: "取消",
        confirmText: "确认",
      },
    },
    record: {
      dialog: {
        editTitle: "编辑记录",
      },
      form: {
        transferRecord: "传输记录",
        sourceName: "来源名称",
        sourcePath: "来源路径",
        destinationPath: "目标路径",
        isEpisode: "是否为剧集",
        season: "季",
        episode: "集",
        status: "状态",
        ignored: "忽略",
        extraInfo: "额外信息",
        number: "编号",
        tags: "标签",
        tagsPlaceholder: "用逗号分隔多个标签",
        tagsHint: "例如：中文字幕,破解",
        partNumber: "部分编号",
        specifiedSource: "指定来源",
        specifiedUrl: "指定URL",
        save: "保存",
        cancel: "取消",
        seasonRule: "季数必须大于等于-1",
        episodeRule: "集数必须大于等于-1",
        partNumberRule: "部分编号必须大于等于0",
        topFolder: "顶层文件夹",
        applyAll: "应用全部",
        topFolderUpdateSuccess: "成功更新所有匹配记录的顶层文件夹",
        topFolderUpdateError: "更新顶层文件夹失败，请重试",
        topFolderMissingData: "源文件夹或顶层文件夹值缺失",
      },
    },
    task: {
      dialog: {
        editTitle: "编辑任务",
        addTitle: "添加任务",
      },
      form: {
        name: "名称",
        description: "描述",
        contentType: "内容类型",
        movie: "电影",
        series: "剧集",
        sourceFolder: "源文件夹",
        outputFolder: "输出文件夹",
        operation: "操作方式",
        hardLink: "硬链接",
        softLink: "软链接",
        move: "移动",
        copy: "复制",
        autoWatch: "自动监视",
        cleanOthers: "清理其他",
        enableScraping: "启用刮削",
        scrapingId: "刮削配置ID",
        selectScraping: "选择刮削配置",
        scrapingHint: '若此处没有您想要的配置, 请在 "刮削配置" 内新增',
        enabled: "启用",
        optimizeName: "优化名称",
        failedFolder: "失败文件夹",
        escapeFolder: "排除文件夹",
        escapeLiterals: "排除文字",
        escapeSize: "排除大小",
        submit: "提交",
      },
    },
    scraping: {
      dialog: {
        editTitle: "编辑刮削配置",
        addTitle: "添加刮削配置",
      },
      form: {
        name: "名称",
        description: "描述",
        saveMetadata: "保存元数据",
        namingRule: "命名规则",
        scrapingSites: "刮削站点",
        locationRule: "位置规则",
        maxTitleLength: "最大标题长度",
        moreStoryline: "更多故事线",
        extraFanartEnabled: "启用额外图片",
        extraFanartFolder: "额外图片文件夹",
        watermarkEnabled: "启用水印",
        watermarkSize: "水印大小",
        watermarkLocation: "水印位置",
        submit: "提交",
        reset: "重置",
      },
    },
  },
}
