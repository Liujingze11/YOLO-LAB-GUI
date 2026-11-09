# DOCS

## Update

### API update

```shell
# update apt docs
sphinx-apidoc -o source/_api ../yolo_backprop/ ../yolo_backprop/segment_any/edge_sam/* ../yolo_backprop/segment_any/mobile_sam/* ../yolo_backprop/segment_any/sam2/* ../yolo_backprop/segment_any/sam3/* ../yolo_backprop/segment_any/segment_anything/* ../yolo_backprop/segment_any/segment_anything_hq/* ../yolo_backprop/segment_any/segment_anything_fast/* ../yolo_backprop/segment_any/segment_anything_med2d/* ../yolo_backprop/ui/* ../yolo_backprop/icons_rc.py -f
```

### Internationalization

```shell
sphinx-build -b gettext ./source/ ./build/gettext/
```

```shell
sphinx-intl update -p ./build/gettext/ -l zh_CN -d source/locales/
```

## Preview

```shell
# build and preview for zh_CN
sphinx-build -b html -D language=zh_CN source ./build/html/zh_CN

# build and preview for en
sphinx-build -b html -D language=en source ./build/html/en
```
