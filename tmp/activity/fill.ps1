$ErrorActionPreference='Stop'
Add-Type -AssemblyName System.IO.Compression
$source='C:/Users/mistero/Downloads/Weeks 6-7 - Individual Tasks.docx'
$dest='C:/Users/mistero/Downloads/Projects/TheEqualizer/output/docx/Week6-7_Tasks_Option_A.docx'
$s=[IO.File]::Open($source,'Open','Read','ReadWrite')
$f=[IO.File]::Create($dest); $s.CopyTo($f); $f.Dispose(); $s.Dispose()
$z=[IO.Compression.ZipFile]::Open($dest,'Update')
$reader=[IO.StreamReader]::new($z.GetEntry('word/document.xml').Open())
[xml]$x=$reader.ReadToEnd(); $reader.Dispose()
$ns='http://schemas.openxmlformats.org/wordprocessingml/2006/main'
$n=[Xml.XmlNamespaceManager]::new($x.NameTable); $n.AddNamespace('w',$ns)
$tables=$x.SelectNodes('//w:body/w:tbl',$n)
function Fill($table,$row,$col,[string[]]$lines){
 $cell=$tables[$table].SelectNodes('w:tr',$n)[$row].SelectNodes('w:tc',$n)[$col]
 $proto=$cell.SelectSingleNode('w:p',$n).CloneNode($true)
 foreach($p in @($cell.SelectNodes('w:p',$n))){[void]$cell.RemoveChild($p)}
 foreach($line in $lines){
  $p=$proto.CloneNode($true)
  foreach($child in @($p.ChildNodes)){if($child.LocalName -ne 'pPr'){[void]$p.RemoveChild($child)}}
  $r=$x.CreateElement('w','r',$ns)
  $pr=$x.CreateElement('w','rPr',$ns)
  foreach($pair in @(@('color','000000'),@('sz','20'),@('szCs','20'))){$el=$x.CreateElement('w',$pair[0],$ns);$el.SetAttribute('val',$ns,$pair[1]);[void]$pr.AppendChild($el)}
  [void]$r.AppendChild($pr)
  $t=$x.CreateElement('w','t',$ns);$t.InnerText=$line;[void]$r.AppendChild($t);[void]$p.AppendChild($r);[void]$cell.AppendChild($p)
 }
}
Fill 2 1 0 @('Option A - Real tech platform or app')
Fill 2 1 1 @('Duolingo')
Fill 2 1 2 @('Duolingo offers short, interactive language lessons through its website and mobile app.')
Fill 3 1 1 @('Duolingo uses subscriptions and advertising. Learners pay recurring fees for Super Duolingo or Duolingo Max to receive extra features, while advertisers pay to reach free users. It is freemium because the basic courses are free and upgrades are optional. Its paid plans provide ongoing access to an online software service rather than ownership of the software. [1]')
Fill 3 2 1 @('Users can find Duolingo on duolingo.com, Google Play, the Apple App Store, and social media such as TikTok. My ratings are: Findable - strong, with a searchable name and direct app links; Consistent - strong, with the green owl and recognizable branding; Accurate - good, with official explanations of free and paid access; Maintained - good, with product news and learning content. One suggested improvement is a clearer country-specific comparison showing available plans, total charges, and renewal terms together. [1, 2]')
Fill 3 3 1 @('Possible problem: a new user comparing free access and paid plans may struggle to identify the full renewal charge before subscribing. Suggested fix: show a simple comparison with the total charge, billing period, and cancellation instructions before confirmation.', 'Test task: "On your phone, find a paid plan, explain how much and when you would be charged, and locate how to cancel without completing a payment." Observe hesitation, mistakes, and completion time, then improve the page and retest.')
Fill 3 4 1 @('Content marketing: Duolingo publishes learning advice, such as its article on studying English independently. It answers a learner need and encourages readers to use the app. I would add a trackable sign-up link to this type of article and measure the number of completed new account registrations from it over 30 days, rather than counting views alone. [3]')
Fill 3 5 1 @('Segment type: demographic. Target users: college students with limited budgets who want to practice a language between classes. Proposed message: "Make your study break count. Practice a new language with short, free Duolingo lessons." This highlights affordability and convenience without inventing a student discount.')
Fill 3 6 1 @('Proposed technique: social/creator advertising. Sponsor a clearly labeled TikTok video where a student creator demonstrates a short beginner lesson and links to the app. This suits students browsing short videos, shows the actual learning experience, and makes the next step clear. Target relevant viewers and measure registrations, not just likes.')
Fill 3 7 1 @('I would recommend a moderated Facebook group for Filipino Duolingo learners. Members could share study routines, ask beginner questions, and celebrate weekly progress. Duolingo could collect feedback and answer common concerns. Peer encouragement could help learners keep practicing and recommend the app to friends, supporting retention and word of mouth.')
Fill 4 1 0 @('Revenue is the money Duolingo receives before expenses; profit is the amount left after paying its costs. For a simplified hypothetical example, suppose 100 subscribers each pay PHP 200 for one month. Subscription revenue would be 100 x PHP 200 = PHP 20,000. If server costs are PHP 4,000, developer and lesson-production costs are PHP 8,000, and payment fees and marketing cost PHP 3,000, total costs are PHP 15,000. Profit would be PHP 20,000 - PHP 15,000 = PHP 5,000. These are illustration amounts, not Duolingo prices or reported financial results.')
Fill 5 1 0 @('Sample reflection to personalize: I would abandon an online purchase if a required sign-up form erased my details whenever a verification code expired. Re-entering the same information would make a simple purchase frustrating. Keeping the information already entered, showing a clear resend-code option and countdown, and allowing guest checkout where appropriate would make me more likely to continue. The business should reduce repeated work while keeping necessary security checks.')
Fill 6 1 0 @('Sample reflection to personalize: The topic I would like clarified is measuring web marketing results. A customer may see a TikTok ad, read a blog post, and subscribe several days later, so deciding which activity produced the sale seems difficult. My question for the next session is: "How can a small app business measure which marketing channel led to a paid subscription when the customer used several channels before paying?"')
# Keep each answer row together and repeat the blueprint header on new pages.
foreach($row in $tables[3].SelectNodes('w:tr',$n)){
 $rp=$row.SelectSingleNode('w:trPr',$n)
 if(!$rp){$rp=$x.CreateElement('w','trPr',$ns);[void]$row.PrependChild($rp)}
 if(!$rp.SelectSingleNode('w:cantSplit',$n)){[void]$rp.AppendChild($x.CreateElement('w','cantSplit',$ns))}
}
# Add compact source references before the original submission guidelines.
$body=$x.SelectSingleNode('//w:body',$n)
foreach($line in @('Sources','[1] Duolingo. Is Duolingo Free for All Learners? https://blog.duolingo.com/is-duolingo-free/','[2] Duolingo official website. https://www.duolingo.com/','[3] Duolingo. How to Study English on Your Own and Tips for Getting Started. https://blog.duolingo.com/how-to-study-english-on-your-own/')){
 $p=$x.CreateElement('w','p',$ns);$r=$x.CreateElement('w','r',$ns);$pr=$x.CreateElement('w','rPr',$ns)
 $sz=$x.CreateElement('w','sz',$ns);$sz.SetAttribute('val',$ns,'18');[void]$pr.AppendChild($sz);[void]$r.AppendChild($pr)
 $t=$x.CreateElement('w','t',$ns);$t.InnerText=$line;[void]$r.AppendChild($t);[void]$p.AppendChild($r);[void]$body.InsertBefore($p,$tables[7])
}
$z.GetEntry('word/document.xml').Delete()
$e=$z.CreateEntry('word/document.xml');$writer=[IO.StreamWriter]::new($e.Open(),[Text.UTF8Encoding]::new($false));$x.Save($writer);$writer.Dispose();$z.Dispose()
Write-Output $dest
