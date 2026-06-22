# AI 查岗路径 · 资料来源汇总

> 最后更新：2026-06-21  
> 目标：**广西+广东 · 环保×计算机交叉方向** · 硕士  
> 规则：无链接=不存在，点到公告/转载≠详情页

---

## 一、直接招聘平台（有岗位详情页，可立刻投递）

### 1. 广西人才网 gxrc.com
```
方式：browser-act 全浏览器 + JS eval
命令：browser-act --session jh browser open chrome_local_101959002016973032 "URL"
提取：eval "JSON.stringify(Array.from(document.querySelectorAll('a[href*=\"/jobDetail/\"]')).map(...))"

搜索URL模板：
  https://s.gxrc.com/sJob?schType=1&keyword={关键词}&sortType=1

已验证有效的关键词（2026-06-21 南宁）：
  - python 开发 → 10条
  - 信息化 人工智能 大数据 → 5条
  - 环保 治理 咨询 → 2条

已验证无效（0结果）：
  - 环保信息化 / 智慧环保 / 环境大数据 / 环境数据分析
```
- 来源类型：✅ 详情页（可直接投递）
- 验证方式：browser-act 逐页抓取
- 可靠性：高

### 2. 前程无忧 51job.com
```
方式：browser-act 全浏览器 + JS eval
命令：browser-act --session w51 navigate "https://we.51job.com/pc/search?keyword={关键词}"
提取：eval "JSON.stringify(Array.from(document.querySelectorAll('.joblist-item')).map(...))"

搜索URL模板：
  https://we.51job.com/pc/search?keyword={关键词}

已验证有效的关键词（全国，需后期按城市筛选）：
  - 环境数据分析 → 15条
  - 智慧环保 → 15条
  - 智慧水务 广州 → 15条
  - 环保大数据 广州 → 15条
  - python开发 → 10条

城市过滤：
  51job的jobArea参数在SPA中不生效
  方案：① 在关键词中拼接城市名（如"环境数据 南宁"） ② 搜索结果中筛选公司所在城市
```
- 来源类型：✅ 详情页（可直接投递）
- 验证方式：browser-act 逐页抓取
- 可靠性：高

### 3. BOSS直聘 zhipin.com
```
方式：browser-act headed 全浏览器 + 手动扫码登录一次
前置：登录后cookie保留在chrome_local，后续无需再登
城市码：南宁=101300100 广州=101300200 深圳=101300800

搜索URL模板：
  https://www.zhipin.com/web/geek/job?query={关键词}&city={城市码}

已验证有效：
  - 南宁 python 开发 → 15条
  - 南宁 环境数据 分析 → 8条
  - 南宁 环保 环境 → 8条

已知限制：
  - 薪资金额因中文数字编码问题，eval提取时显示不全
  - 频繁搜索会触发验证码（需手动点一下）
```
- 来源类型：✅ 详情页（可直接投递）
- 验证方式：browser-act headed模式登录后抓取
- 可靠性：高（需保持登录态）

---

## 二、大学环境学院就业网（招聘平台搜不到的富矿）

### 4. 广西大学·资源环境与材料学院 就业信息
```
地址：https://gxulif.gxu.edu.cn/CN/rcpy/jyxx.htm
方式：browser-act stealth-extract（无登录，纯静态）
分页：22页，URL模式 https://gxulif.gxu.edu.cn/CN/rcpy/jyxx/{页码}.htm
      第1页：jyxx.htm，第2页：jyxx/21.htm，第3页：jyxx/20.htm……第22页：jyxx/1.htm

提取说明：
  公司来学院官网发布招聘简章 → 简章包含岗位+投递邮箱/网申入口
  链接类型是简章页（非招聘平台详情页），但通常包含直接投递渠道
```
- 来源类型：⚠️ 简章页（非招聘平台，但包含投递邮箱）
- 验证方式：browser-act stealth-extract 已验证可访问
- 可靠性：高（学院官方发布）

### 5. 桂林理工大学·环境科学与工程学院 访企拓岗/就业
```
地址：https://hjxy.glut.edu.cn/xwzx1/fqtg.htm （访企拓岗·7页）
      首页：fqtg.htm，第2页：fqtg/6.htm，第3页：fqtg/5.htm
      通知公告：https://hjxy.glut.edu.cn/xwzx1/tzgg1.htm
      学院新闻：https://hjxy.glut.edu.cn/xwzx1/xyxw1.htm
方式：browser-act stealth-extract（无登录，纯静态）

已发现的关键招聘信息（第一页）：
  - 广东德尔智慧科技·环境工程专场招聘会 (5/12)
  - 上海秦望环保材料·环境工程专场招聘会 (4/27)
  - 湛江规划勘测设计院·环境工程+给排水 (4/23)
  - 广西水利科学研究院·访企拓岗 (4/13)
  - 深圳中金岭南·韶关冶炼厂招聘会 (3/26)
```
- 来源类型：⚠️ 简章/新闻页（非招聘平台，但包含公司+岗位信息）
- 验证方式：browser-act stealth-extract 已验证可访问
- 可靠性：高（学院官方发布）

### 6. 广西民族大学·材料与环境学院 & 应用技术学院 就业
```
就业信息：应用技术学院招生就业栏 https://yyjsxy.gxmzu.edu.cn/zsjy.htm
招聘会报道：https://yyjsxy.gxmzu.edu.cn/info/1065/4851.htm（46企·4院联合·2025/11/8）
```
- 来源类型：⚠️ 简章/新闻页
- 验证方式：browser-act stealth-extract 已验证
- 可靠性：高

### 7. 南宁师范大学·环境与生命科学学院 就业
```
新闻动态：http://hjsmxy.nnnu.edu.cn/xyxw/xwdt.htm
通知公告：http://hjsmxy.nnnu.edu.cn/xyxw/tzgg.htm
双选会报道：http://hjsmxy.nnnu.edu.cn/info/1041/4891.htm（5/6四院联合春招）
```
- 来源类型：⚠️ 新闻页
- 验证方式：browser-act stealth-extract 已验证
- 可靠性：高

### 8. 百色学院·农业与食品工程学院 就业
```
学院官网：http://nxy.bsuc.edu.cn
双选会报道：http://nxy.bsuc.edu.cn/info/1149/7202.htm（130+企，400+岗位，2025/12/12）
```
- 来源类型：⚠️ 新闻页
- 验证方式：WebSearch
- 可靠性：中（待 browser-act 验证）

### 9. 桂林电子科技大学·生命与环境科学学院 就业
```
学院官网：https://www.guet.edu.cn 搜索"生命与环境科学学院 就业"
已确认：2025/10/14召开了2026届就业动员会
```
- 来源类型：⚠️ 新闻/公告页
- 验证方式：WebSearch
- 可靠性：中（待 browser-act 验证）

### 10. 待扩展（广西）
```
  - 广西科技大学·生物与化学工程学院（环境方向）
  - 广西师范大学·环境与资源学院：http://www.ce.gxnu.edu.cn/
```

---

## 广东大学环境学院就业网（新增）

### 11. 华南理工大学·环境与能源学院 就业
```
就业在线：https://www2.scut.edu.cn/cese/1533/list.htm
学校就业中心：https://jyzx.scut.edu.cn/
就业负责人：本科 李文杰老师 020-81182711 / 研究生 王健老师 020-81182710
地址：广州大学城外环东路382号 环境大楼
```
- 来源类型：⚠️ 简章/就业信息页（学院不直接发布简章，引导到学校就业中心）
- 验证方式：browser-act stealth-extract 已验证可访问
- 可靠性：高
- 说明：学院就业页主要提供就业指导，具体招聘信息集中在学校就业中心 jyzx.scut.edu.cn

### 12. 中山大学·环境科学与工程学院 就业
```
学校就业中心：https://career.sysu.edu.cn/
学院官网：https://sese.sysu.edu.cn/
招聘系统：https://recruit.sysu.edu.cn/
2026届校招：广州校区6/5已举办，珠海校区6/12已举办
```
- 来源类型：⚠️ 学校就业中心为主
- 验证方式：WebSearch
- 可靠性：高

### 13. 广东工业大学·环境科学与工程学院 就业
```
学校就业中心：https://career.gdut.edu.cn/
学院就业联系：王焕老师（每周二/五下午可咨询）
2026届招聘会：146家企业参会，743个岗位
```
- 来源类型：⚠️ 学校就业中心为主
- 验证方式：WebSearch
- 可靠性：高

### 14. 暨南大学·环境学院（待验证）
```
学院官网：https://hjxy.jnu.edu.cn/
就业中心：https://career.jnu.edu.cn/
```
- 状态：待下一次搜索验证

### 15. 广州大学·环境科学与工程学院（待验证）
```
学院官网：http://environ.gzhu.edu.cn/
```
- 状态：待下一次搜索验证

---

## 三、事业单位/政府渠道（公告页，需找投递入口）

### 7. 广西生态环境厅直属单位
```
广西环境信息中心：
  公告地址：http://sthjt.gxzf.gov.cn/zfxxgk/zfxxgkgl/fdzdgknr/rsgl/zkxx/t27298550.shtml
  说明：政府网站，非招聘平台。需打开公告查看邮箱/报名方式

广西环境保护科学研究院：
  GXRC详情页（已过期）：https://www.gxrc.com/jobDetail/0707a6d937ca444b85214d52e2e6978a
  说明：4/10截止。可关注GXRC事业单位频道或广西环科院官网等下一批
```
- 来源类型：⚠️ 公告页（需多一步找投递方式）
- 验证方式：WebSearch + browser-act 验证
- 可靠性：中（公告可能已过期，需确认）

### 8. 生态环境部直属单位
```
生态环境部华南环境科学研究所（广州）：
  公告地址：https://www.scies.org/gzdt/gsl/rcyjyzp/202603/t20260321_1147404.shtml
  说明：browser-act已验证页面存在。27岗位，报名4/22截止。硕士可报海洋AI岗
  报名入口：https://f.wps.cn/g/zQg4KZrp/
```
- 来源类型：⚠️ 公告页（报名入口是WPS表单，非招聘平台）
- 验证方式：browser-act 全浏览器模式已验证
- 可靠性：高（生态环境部官方发布）

---

## 四、公务员/编制渠道

### 9. 广西公务员考试
```
南宁市生态环境保护综合行政执法支队·执法信息化建设职位：
  转载页：https://ah.huatu.com/zw/gxgwy/2026/399.html（华图转载，非官方）
  官方入口：需去广西人事考试网(gxpta.com.cn)找2026年广西公务员考试职位表
```
- 来源类型：⚠️ 第三方转载（需去官方入口）
- 验证方式：WebSearch
- 可靠性：中（转载信息需官方确认）

---

## 五、已验证无结果或已放弃的渠道

以下渠道反复搜索但未找到广西+广东+环保×计算机的岗位，记录在此避免重复劳动：

```
- GXRC关键词"环保信息化" → 0结果
- GXRC关键词"智慧环保" → 0结果
- GXRC关键词"环境大数据" → 0结果
- GXRC关键词"环境数据分析" → 0结果
- GXRC关键词"智慧水务" → 0结果（只有水务+信息化+数据搜到1条非环境岗）
- 51job关键词"环境监测 南宁" → 0结果
- 51job关键词"环境数据 南宁" → 仅溢出广州岗位
- BOSS移动版(m.zhipin.com) → 被反爬拦截
- 桂聘网guipin.com → httpx+BS4代码已写但待实际搜索验证
```

---

## 六、AI执行流程

AI每次查岗时按以下顺序执行：

```
步骤1：GXRC 搜索（最近3天）
  └→ 关键词=python 开发, 信息化 人工智能 大数据
  └→ 提取 a[href*="/jobDetail/"] → 有链接=保留

步骤2：51job 搜索
  └→ 关键词=环境数据分析, 智慧水务 广州, 环保大数据 广州
  └→ 提取 .joblist-item → 有链接=保留

步骤3：BOSS直聘（如果登录态有效）
  └→ 关键词=python, 环境数据, 环保
  └→ 城市码=101300100(南宁)
  └→ 提取 job-card → 有链接=保留

步骤4：广西大学环境学院就业网
  └→ stealth-extract 第1-5页
  └→ 从Markdown中提取公司名+岗位关键词
  └→ 筛选"环境×计算机"相关的条目

步骤5：桂林理工环境学院就业网
  └→ stealth-extract 访企拓岗+通知公告
  └→ 同上提取筛选

步骤6：汇总
  └→ 每条标注来源+链接类型+验证状态
  └→ 剔除：非广西/广东、纯计算机无环保属性、纯环保无技术含量
```

---

## 七、链接类型标注规范

最终报告必须标注每个岗位的链接类型：

| 标注 | 含义 | 可直接投递 |
|:----|------|:--:|
| ✅ 详情页 | 点击直达招聘网站岗位详情，有投递按钮 | 是 |
| ⚠️ 简章页 | 学院/公司官网简章，需找邮箱或网申入口 | 否，需多一步 |
| ⚠️ 公告页 | 政府/事业单位公告，需按要求发邮件 | 否，需多一步 |
| ⚠️ 转载页 | 华图/本地宝/高校就业网转载，非源头 | 否，需去官方渠道 |
