-- 补丁：fams_asset_scrap 表缺少 update_time 列，导致 ScrapDao.update_by_biz_id 失败
-- 错误症状：报废申请提交时报 "系统配置异常，请联系管理员"（底因：no such column: update_time）

ALTER TABLE fams_asset_scrap ADD COLUMN update_time DATETIME;
UPDATE fams_asset_scrap SET update_time = create_time WHERE update_time IS NULL;
