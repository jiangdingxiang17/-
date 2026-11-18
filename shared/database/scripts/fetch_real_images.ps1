# ============================================================
# 在线生鲜商城 - 真实图片 URL 获取脚本 (PowerShell)
# ============================================================
# 用途：通过 SourceSplash API 为每个商品搜索真实食品图片
#       过滤掉 Picsum 占位图，只保留 Pexels/Pixabay 等真实图源
# 输出：seed_data.sql（直接覆盖更新）
# ============================================================

$ErrorActionPreference = "Continue"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = Split-Path -Parent (Split-Path -Parent (Split-Path -Parent $scriptDir))
$dmlDir = Join-Path $projectRoot "shared\database\dml"
$sqlFile = Join-Path $dmlDir "seed_data.sql"
$cacheFile = Join-Path $scriptDir "image_cache.json"

# ============================================================
# 关键词映射（中文商品名 → 英文搜索关键词，优化用于 SourceSplash）
# ============================================================
$keywords = @{
    # === 蔬菜（30个）===
    '西红柿'     = 'fresh tomato vegetable market'
    '黄瓜'       = 'fresh cucumber green vegetable'
    '菠菜'       = 'fresh spinach leaves green'
    '土豆'       = 'fresh potato raw vegetable'
    '大白菜'     = 'napa cabbage vegetable fresh'
    '生菜'       = 'fresh lettuce salad green'
    '胡萝卜'     = 'fresh carrot vegetable orange'
    '西兰花'     = 'fresh broccoli green vegetable'
    '芹菜'       = 'fresh celery green vegetable'
    '青椒'       = 'fresh green pepper bell vegetable'
    '茄子'       = 'fresh eggplant purple vegetable'
    '豆角'       = 'fresh green beans vegetable'
    '南瓜'       = 'fresh pumpkin vegetable'
    '甜玉米'     = 'fresh sweet corn vegetable'
    '韭菜'       = 'fresh chives green herb'
    '洋葱'       = 'fresh onion vegetable'
    '冬瓜'       = 'winter melon gourd fresh'
    '莲藕'       = 'fresh lotus root vegetable'
    '山药'       = 'fresh yam vegetable chinese'
    '苦瓜'       = 'fresh bitter gourd vegetable'
    '蒜苗'       = 'fresh garlic sprouts green'
    '红薯'       = 'fresh sweet potato vegetable'
    '丝瓜'       = 'fresh luffa gourd vegetable'
    '秋葵'       = 'fresh okra vegetable green'
    '空心菜'     = 'fresh water spinach greens'
    '白萝卜'     = 'fresh daikon radish white vegetable'
    '莴笋'       = 'fresh celtuce stem vegetable'
    '花菜'       = 'fresh cauliflower white vegetable'
    '茼蒿'       = 'fresh crown daisy greens'
    '娃娃菜'     = 'fresh baby cabbage vegetable'

    # === 水果（32个）===
    '红富士苹果'   = 'fresh fuji apple fruit red'
    '香蕉'         = 'fresh banana fruit yellow'
    '阳光玫瑰葡萄' = 'fresh green grapes fruit shine muscat'
    '海南金钻菠萝' = 'fresh golden pineapple fruit'
    '丹东草莓'     = 'fresh strawberry fruit red'
    '海南芒果'     = 'fresh mango fruit yellow'
    '麒麟西瓜'     = 'fresh watermelon fruit'
    '赣南脐橙'     = 'fresh navel orange fruit'
    '徐香猕猴桃'   = 'fresh kiwifruit green fruit'
    '智利车厘子'   = 'fresh cherry fruit red'
    '妃子笑荔枝'   = 'fresh lychee fruit'
    '红心火龙果'   = 'fresh dragon fruit pink'
    '秘鲁蓝莓'     = 'fresh blueberry fruit'
    '文旦柚'       = 'fresh pomelo citrus fruit'
    '阳山水蜜桃'   = 'fresh peach fruit'
    '新疆哈密瓜'   = 'fresh melon cantaloupe fruit'
    '龙眼'         = 'fresh longan fruit'
    '山竹'         = 'fresh mangosteen fruit purple'
    '阿克苏苹果'   = 'fresh apple fruit red'
    '突尼斯软籽石榴' = 'fresh pomegranate fruit red'
    '海南椰子'     = 'fresh coconut fruit'
    '金枕榴莲'     = 'fresh durian fruit'
    '樱桃番茄'     = 'fresh cherry tomato fruit'
    '红提'         = 'fresh red grapes fruit'
    '库尔勒香梨'   = 'fresh pear fruit'
    '百香果'       = 'fresh passion fruit'
    '砂糖橘'       = 'fresh mandarin orange fruit'
    '释迦果'       = 'fresh sugar apple fruit'
    '杨梅'         = 'fresh bayberry fruit red'
    '青提'         = 'fresh green grapes fruit'
    '澳洲无籽红提' = 'fresh red seedless grapes fruit'
    '柠檬'         = 'fresh lemon fruit yellow'

    # === 肉类（32个）===
    '黑猪五花肉'   = 'raw pork belly fresh meat butcher'
    '散养土鸡'     = 'whole raw chicken fresh poultry'
    '安格斯牛排'   = 'raw beef steak fresh meat'
    '猪里脊肉'     = 'raw pork tenderloin fresh meat'
    '澳洲牛腩'     = 'raw beef brisket fresh meat'
    '羊腿肉'       = 'raw lamb leg fresh meat'
    '鸡胸肉'       = 'raw chicken breast fresh meat'
    '半片鸭'       = 'raw duck fresh poultry meat'
    '猪小排'       = 'raw pork ribs fresh meat'
    '金钱腱'       = 'raw beef shank fresh meat'
    '鸡翅中'       = 'raw chicken wings fresh'
    '猪肉馅'       = 'ground pork raw meat fresh'
    '金华火腿'     = 'cured ham dried meat'
    '牛腱子'       = 'raw beef shank fresh meat'
    '猪蹄'         = 'raw pork trotter fresh meat'
    '鸡腿'         = 'raw chicken drumstick fresh'
    '羊排'         = 'raw lamb rack fresh meat'
    '牛尾'         = 'raw oxtail fresh meat'
    '鸭胸肉'       = 'raw duck breast fresh meat'
    '猪肉片'       = 'raw pork slice fresh meat'
    '鸡爪'         = 'raw chicken feet fresh'
    '牛百叶'       = 'beef tripe omasum fresh'
    '猪肝'         = 'raw pork liver fresh meat'
    '肥牛卷'       = 'raw beef slice fresh meat roll'
    '乌鸡'         = 'raw silkie chicken black poultry'
    '牛里脊'       = 'raw beef tenderloin fresh meat'
    '培根'         = 'raw bacon strips fresh meat'
    '猪大肠'       = 'raw pork intestine fresh meat'
    '腊肉'         = 'chinese cured pork belly dried meat'
    '牛肉馅'       = 'ground beef raw meat fresh'
    '鸽子'         = 'raw pigeon squab fresh poultry'
    '鸡胗'         = 'raw chicken gizzard fresh meat'

    # === 鱼类/海鲜（31个）===
    '活鲫鱼'       = 'fresh crucian carp fish market'
    '三文鱼刺身'   = 'raw salmon fillet fresh fish seafood'
    '北极甜虾'     = 'raw shrimp fresh seafood'
    '东海带鱼'     = 'fresh hairtail fish seafood market'
    '黄花鱼'       = 'fresh yellow croaker fish market'
    '海鲈鱼'       = 'fresh sea bass fish market'
    '基围虾'       = 'raw shrimp fresh seafood market'
    '乳山生蚝'     = 'fresh oyster raw seafood'
    '扇贝'         = 'fresh scallop raw seafood'
    '鱿鱼'         = 'raw squid fresh seafood'
    '金鲳鱼'       = 'fresh pomfret fish seafood market'
    '花蛤'         = 'fresh clams seafood market'
    '大连海参'     = 'dried sea cucumber seafood'
    '多宝鱼'       = 'fresh turbot fish seafood market'
    '银鳕鱼'       = 'raw cod fillet fresh fish seafood'
    '象拔蚌'       = 'fresh geoduck clam seafood'
    '石斑鱼'       = 'fresh grouper fish seafood market'
    '皮皮虾'       = 'raw mantis shrimp fresh seafood'
    '蛏子'         = 'fresh razor clams seafood market'
    '鲍鱼'         = 'fresh abalone raw seafood'
    '小龙虾'       = 'raw crayfish fresh seafood'
    '草鱼'         = 'fresh grass carp fish market'
    '墨鱼仔'       = 'raw baby cuttlefish seafood'
    '海蜇'         = 'fresh jellyfish seafood'
    '甲鱼'         = 'fresh softshell turtle'
    '秋刀鱼'       = 'fresh saury fish seafood market'
    '鳕鱼排'       = 'raw cod fillet fresh fish seafood'
    '海螺'         = 'fresh conch seashell seafood'
    '鳊鱼'         = 'fresh bream fish market'
    '蟹肉棒'       = 'crab stick seafood surimi'
    '黑鱼'         = 'fresh snakehead fish market'
}

# ============================================================
# 备用关键词（当主要搜索返回 Picsum 时尝试）
# ============================================================
$fallbackKeywords = @{
    '胡萝卜'   = 'carrot vegetable fresh market'
    '西兰花'   = 'broccoli vegetable green fresh'
    '韭菜'     = 'garlic chives herb green'
    '蒜苗'     = 'leek green vegetable fresh'
    '豆角'     = 'string beans green vegetable'
    '肉馅'     = 'minced meat raw fresh ground'
    '鸽子'     = 'pigeon bird poultry fresh'
    '海蜇'     = 'jellyfish seafood asian food'
    '甲鱼'     = 'turtle softshell food fresh'
    '蟹肉棒'   = 'imitation crab meat seafood stick'
}

# ============================================================
# 主函数
# ============================================================
Write-Host "=" * 65
Write-Host "  生鲜商城 - 真实图片 URL 获取工具"
Write-Host "  数据源: SourceSplash API (Pexels/Pixabay 图片)"
Write-Host "=" * 65

# 读取缓存
$cache = @{}
if (Test-Path $cacheFile) {
    try {
        $cache = Get-Content $cacheFile -Raw | ConvertFrom-Json -AsHashtable
        Write-Host "[缓存] 已加载 $(($cache.Keys).Count) 条缓存记录"
    } catch {
        Write-Host "[缓存] 无法加载缓存，将重新获取"
        $cache = @{}
    }
}

$results = @{}
$total = $keywords.Keys.Count
$current = 0
$failCount = 0
$picsumCount = 0

Write-Host "`n[开始] 共 $total 个商品，逐个搜索中...`n"

foreach ($productName in $keywords.Keys) {
    $current++
    $query = $keywords[$productName]
    
    # 检查缓存
    if ($cache.ContainsKey($productName) -and $cache[$productName] -ne "") {
        $results[$productName] = $cache[$productName]
        Write-Host "[$current/$total] $productName → 缓存命中"
        continue
    }
    
    $imageUrl = ""
    $triedFallback = $false
    
    :searchLoop while ($true) {
        $searchQuery = if ($triedFallback) { 
            $fallbackKeywords[$productName] 
        } else { 
            $query 
        }
        
        if (-not $searchQuery) { break }
        
        $encodedQuery = [uri]::EscapeDataString($searchQuery)
        $apiUrl = "https://www.sourcesplash.com/api/search?q=$encodedQuery&per_page=1"
        
        try {
            $response = Invoke-RestMethod -Uri $apiUrl -Method Get -TimeoutSec 10
            
            if ($response.results -and $response.results.Count -gt 0) {
                $result = $response.results[0]
                $source = $result.source
                $id = $result.id
                
                if ($source -ne "picsum") {
                    # 使用 SourceSplash 的直链 URL，尺寸 400x300
                    $imageUrl = "https://www.sourcesplash.com/i/$id"
                    Write-Host "[$current/$total] $productName → [$source] OK"
                    break
                } else {
                    # Picsum 结果，尝试备用关键词
                    if (-not $triedFallback -and $fallbackKeywords.ContainsKey($productName)) {
                        $triedFallback = $true
                        Write-Host "[$current/$total] $productName → [picsum] 尝试备用关键词..."
                        continue
                    } else {
                        Write-Host "[$current/$total] $productName → [picsum] 无备用词，使用 Picsum"
                        $imageUrl = "https://www.sourcesplash.com/i/$id"
                        $picsumCount++
                        break
                    }
                }
            } else {
                Write-Host "[$current/$total] $productName → [无结果]"
                $failCount++
                break
            }
        } catch {
            Write-Host "[$current/$total] $productName → [请求失败] $($_.Exception.Message.Substring(0, [Math]::Min(40, $_.Exception.Message.Length)))"
            $failCount++
            break
        }
    }
    
    $results[$productName] = $imageUrl
    
    # 避免请求过快
    Start-Sleep -Milliseconds 300
}

Write-Host "`n[完成] 成功: $($total - $failCount) | 失败: $failCount | Picsum 占位: $picsumCount`n"

# 保存缓存
$results | ConvertTo-Json | Set-Content $cacheFile -Encoding UTF8
Write-Host "[缓存] 已保存到 $cacheFile`n"

# ============================================================
# 更新 seed_data.sql
# ============================================================
Write-Host "[更新] 正在更新 seed_data.sql ..."

if (-not (Test-Path $sqlFile)) {
    Write-Host "[错误] 找不到文件: $sqlFile"
    exit 1
}

$sqlContent = Get-Content $sqlFile -Raw -Encoding UTF8
$lines = $sqlContent -split "`r?`n"
$newLines = @()

# 匹配产品行的正则
$productLinePattern = [regex]::new(
    "^(\s*\('([^']+)',\s*'([^']+)',\s*[\d.]+\s*,\s*\d+\s*,\s*\d+\s*,\s*)'[^']*'(\s*,\s*'[^']*'\)[,;]?\s*)$"
)

$updatedCount = 0

foreach ($line in $lines) {
    $m = $productLinePattern.Match($line)
    if ($m.Success) {
        $beforeUrl = $m.Groups[1].Value
        $name = $m.Groups[2].Value
        $afterUrl = $m.Groups[4].Value
        
        if ($results.ContainsKey($name) -and $results[$name] -ne "") {
            $newUrl = $results[$name]
            $newLine = "$beforeUrl'$newUrl'$afterUrl"
            $newLines += $newLine
            $updatedCount++
        } else {
            # 保留原 URL（如果搜索结果为空）
            $newLines += $line
        }
    } else {
        $newLines += $line
    }
}

# 更新 header 注释
$newContent = ($newLines -join "`r`n")

# 替换 header 中的图片来源说明
$newContent = $newContent -replace '图片来源：Picsum.*$', '图片来源：SourceSplash API（Pexels/Pixabay 真实食品摄影）' -replace 'URL 格式：https://picsum\.photos/seed/\{keyword\}/400/300', 'URL 格式：https://www.sourcesplash.com/i/{id}'

Set-Content $sqlFile -Value $newContent -Encoding UTF8 -NoNewline
Write-Host "[更新] 已更新 $updatedCount 个商品的图片 URL"
Write-Host "[输出] $sqlFile`n"

# ============================================================
# 打印统计信息
# ============================================================
Write-Host "=" * 65
Write-Host "  图片 URL 获取完成！"
Write-Host "  成功获取: $($total - $failCount)/$total 个"
if ($picsumCount -gt 0) {
    Write-Host "  [注意] $picsumCount 个商品使用了 Picsum 占位图"
    Write-Host "         可运行脚本重试以获取更多真实图片"
}
Write-Host "=" * 65

