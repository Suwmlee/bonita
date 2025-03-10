export default {
  app: {
    title: 'Bonita',
    description: 'Bonita 前端应用',
  },
  navitems: {
    dashboard: '仪表盘',
    records: '记录',
    tasks: '任务配置',
    scraping: '刮削配置',
    metadata: '元数据',
    tools: '工具',
    serviceSettings: '服务设置',
    userSettings: '用户设置',
  },
  common: {
    save: '保存',
    cancel: '取消',
    confirm: '确认',
    delete: '删除',
    edit: '编辑',
    add: '添加',
    search: '搜索',
    back: '返回',
    submit: '提交',
    loading: '加载中...',
    noData: '暂无数据',
    success: '成功',
    failed: '失败',
    unknown: '未知',
    yes: '是',
    no: '否',
    all: '全部',
    more: '更多',
    refresh: '刷新',
    next: '下一步',
    prev: '上一步',
    optional: '可选',
    required: '必填',
  },
  auth: {
    login: '登录',
    logout: '退出登录',
    register: '注册',
    username: '用户名',
    password: '密码',
    email: '电子邮箱',
    forgotPassword: '忘记密码',
    rememberMe: '记住我',
    loginSuccess: '登录成功',
    loginFailed: '登录失败',
    invalidCredentials: '用户名或密码错误',
  },
  menu: {
    home: '首页',
    dashboard: '仪表盘',
    settings: '设置',
    profile: '个人资料',
    users: '用户管理',
    roles: '角色管理',
    permissions: '权限管理',
  },
  language: {
    zh: '中文',
    en: '英文',
    switchSuccess: '语言切换成功',
  },
  time: {
    today: '今天',
    yesterday: '昨天',
    tomorrow: '明天',
    day: '天',
    week: '周',
    month: '月',
    year: '年',
    hour: '小时',
    minute: '分钟',
    second: '秒',
  },
  errors: {
    networkError: '网络错误，请检查您的网络连接',
    serverError: '服务器错误，请稍后再试',
    notFound: '未找到资源',
    forbidden: '无权访问',
    unauthorized: '未授权访问',
    timeout: '请求超时',
    unknown: '未知错误',
  },
  validation: {
    required: '{field}不能为空',
    minLength: '{field}长度不能少于{length}个字符',
    maxLength: '{field}长度不能超过{length}个字符',
    email: '请输入有效的电子邮箱地址',
    url: '请输入有效的URL',
    numeric: '请输入数字',
    alpha: '只能输入字母',
    alphaNum: '只能输入字母和数字',
  },
} 