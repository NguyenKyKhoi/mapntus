-- 1. Tạo Database (chỉ tạo nếu chưa có)
IF DB_ID('NTU_WebGIS') IS NULL
    CREATE DATABASE NTU_WebGIS;
GO

-- 2. Chuyển vào sử dụng Database
USE NTU_WebGIS;
GO

-- 3. Tạo bảng NTU_DuongDi khớp với file NTU_DuongDi_WKT.csv (bản có cột WKT)
IF OBJECT_ID('dbo.NTU_DuongDi', 'U') IS NOT NULL
    DROP TABLE dbo.NTU_DuongDi;
GO

CREATE TABLE dbo.NTU_DuongDi (
    Id       INT IDENTITY(1,1) PRIMARY KEY,   -- khóa riêng của bảng
    fid      INT           NULL,              -- KHÔNG đặt khóa chính: dữ liệu có 2 dòng cùng fid = 57530
    osm_id   BIGINT        NULL,              -- mã OSM, dùng BIGINT thay vì FLOAT để không mất chính xác
    code     INT           NULL,
    fclass   NVARCHAR(50)  NULL,              -- service / footway / steps / residential / tertiary
    name     NVARCHAR(200) NULL,
    ref      NVARCHAR(50)  NULL,              -- cột này trong dữ liệu đang để trống
    oneway   NVARCHAR(10)  NULL,
    maxspeed INT           NULL,
    layer    INT           NULL,
    bridge   NVARCHAR(10)  NULL,
    tunnel   NVARCHAR(10)  NULL,
    wkt      NVARCHAR(MAX) NULL,              -- chuỗi LINESTRING lấy từ CSV
    geom     GEOGRAPHY     NULL               -- hình học, tạo từ cột wkt ở bước 5
);
GO

-- 4. Nạp dữ liệu: trong SSMS chuột phải database NTU_WebGIS -> Tasks -> Import Flat File...
--    chọn NTU_DuongDi_WKT.csv, đặt "Table name" là NTU_DuongDi (chọn bảng đã có) và map cột theo TÊN
--    (cột WKT trong CSV -> cột wkt trong bảng; bỏ qua cột Id và geom).

-- 5. Sau khi nạp xong, tạo cột hình học từ chuỗi WKT (kinh độ trước, vĩ độ sau, hệ WGS84 = 4326)
UPDATE dbo.NTU_DuongDi
SET geom = geography::STGeomFromText(wkt, 4326).MakeValid()
WHERE wkt IS NOT NULL;
GO

-- 6. Kiểm tra: số dòng và chiều dài từng đoạn (mét)
SELECT COUNT(*) AS so_doan FROM dbo.NTU_DuongDi;
SELECT TOP 10 name, fclass, geom.STLength() AS chieu_dai_m FROM dbo.NTU_DuongDi;
GO