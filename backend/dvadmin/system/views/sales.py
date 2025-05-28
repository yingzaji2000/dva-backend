import hashlib

from django.contrib.auth.hashers import make_password, check_password
from rest_framework import serializers

from dvadmin.system.models import Sales
from dvadmin.system.models import FieldPermission, MenuField
from rest_framework.viewsets import ModelViewSet
from dvadmin.utils.models import get_custom_app_models, CoreModel
class SalesSerializer(serializers.ModelSerializer):


    class Meta:
        model = Sales
        fields = "__all__"
        # read_only_fields = ["id"]
        # exclude = ["password"]




# class UserCreateSerializer(CustomModelSerializer):
#     """
#     用户新增-序列化器
#     """

#     username = serializers.CharField(
#         max_length=50,
#         validators=[
#             CustomUniqueValidator(queryset=Users.objects.all(), message="账号必须唯一")
#         ],
#     )
#     password = serializers.CharField(
#         required=False,
#     )

#     def validate_password(self, value):
#         """
#         对密码进行验证
#         """
#         md5 = hashlib.md5()
#         md5.update(value.encode('utf-8'))
#         md5_password = md5.hexdigest()
#         return make_password(md5_password)

#     def save(self, **kwargs):
#         data = super().save(**kwargs)
#         data.dept_belong_id = data.dept_id
#         data.save()
#         data.post.set(self.initial_data.get("post", []))
#         return data

#     class Meta:
#         model = Users
#         fields = "__all__"
#         read_only_fields = ["id"]
#         extra_kwargs = {
#             "post": {"required": False},
#             "mobile": {"required": False},
#         }



# class ExportUserProfileSerializer(CustomModelSerializer):
#     """
#     用户导出 序列化器
#     """

#     last_login = serializers.DateTimeField(
#         format="%Y-%m-%d %H:%M:%S", required=False, read_only=True
#     )
#     is_active = serializers.SerializerMethodField(read_only=True)
#     dept_name = serializers.CharField(source="dept.name", default="")
#     dept_owner = serializers.CharField(source="dept.owner", default="")
#     gender = serializers.CharField(source="get_gender_display", read_only=True)

#     def get_is_active(self, instance):
#         return "启用" if instance.is_active else "停用"

#     class Meta:
#         model = Users
#         fields = (
#             "username",
#             "name",
#             "email",
#             "mobile",
#             "gender",
#             "is_active",
#             "last_login",
#             "dept_name",
#             "dept_owner",
#         )

from dvadmin.utils.filters import DataLevelPermissionsFilter, CoreModelFilterBankend
from dvadmin.utils.json_response import ErrorResponse, DetailResponse, SuccessResponse
from django.db import transaction
from datetime import datetime
import json
class SalesViewSet(ModelViewSet):
    queryset = Sales.objects.all()
    serializer_class = SalesSerializer
    
    extra_filter_class = [CoreModelFilterBankend,DataLevelPermissionsFilter]
    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        status = request.query_params.get('status')
        business_name = request.query_params.get('business_name')
        downstream_receiver_name = request.query_params.get('downstream_receiver_name')
        # 初始化 custom_field1 列表
        custom_field1 = []
        # 遍历 QueryDict，提取 customField1 的值
        for key, value in request.query_params.items():
            if key.startswith('customField1[') and key.endswith(']'):
                # 提取索引值并获取对应的值
                custom_field1.append(value)  # 直接获取对应的值
        # 打印 customField1 的值
        print("customField1:", custom_field1)
        # 如果 customField1 有两个值，过滤 outbound_date 在这个时间范围内的记录
        if len(custom_field1) == 2:
            try:
                # 将字符串日期转换为 datetime 对象
                start_date = custom_field1[0]
                end_date = custom_field1[1]
                
                # 过滤 outbound_date 在这个时间范围内的记录
                queryset = queryset.filter(outbound_date__range=(start_date, end_date))
            except ValueError:
                # 如果日期格式不正确，打印错误信息
                print("Invalid date format in customField1. Expected format: YYYY-MM-DD")
        if status =='uncleaned':
            queryset = queryset.exclude(cleaned_result='1')  # 假设你的 Sales 模型有 status 字段
        else:
            queryset = queryset.filter(cleaned_result='1')
        # print(query_params)
        if business_name:
            queryset = queryset.filter(business_name=business_name)
        if downstream_receiver_name:
            queryset = queryset.filter(downstream_receiver_name=downstream_receiver_name)
        page = self.paginate_queryset(queryset)
        if page is not None:
            # 将 request 放入 context 中
            serializer = self.get_serializer(page, many=True, context={'request': request})
            # print(serializer.data)
            return self.get_paginated_response(serializer.data)
        # 同样修改非分页情况下的调用
        serializer = self.get_serializer(queryset, many=True, context={'request': request})
        return SuccessResponse(data=serializer.data, msg="获取成功")
    
    def get_serializer(self, *args, **kwargs):
        print("this is a test6!===========================")
        serializer_class = self.get_serializer_class()
        print("this is a test7!===========================")
        kwargs.setdefault('context', self.get_serializer_context())
        # 全部以可见字段为准
        can_see = self.get_menu_field(serializer_class)
        # 排除掉序列化器级的字段
        # sub_set = set(serializer_class._declared_fields.keys()) - set(can_see)
        # for field in sub_set:
        #     serializer_class._declared_fields.pop(field)
        # if not self.request.user.is_superuser:
        #     serializer_class.Meta.fields = can_see
        # 在分页器中使用
        
        self.request.permission_fields = can_see
        print("this is a test8!===========================")
        if isinstance(self.request.data, list):
            print("this is a test9!===========================")
            with transaction.atomic():
                return serializer_class(many=True, *args, **kwargs)
        else:
            print("this is a test10!===========================")
            return serializer_class(*args, **kwargs)

    def filter_queryset(self, queryset):
        for backend in set(set(self.filter_backends) | set(self.extra_filter_class or [])):
            queryset = backend().filter_queryset(self.request, queryset, self)
        return queryset

    def get_queryset(self):
        if getattr(self, 'values_queryset', None):
            return self.values_queryset
        return super().get_queryset()

    def get_serializer_class(self):
        action_serializer_name = f"{self.action}_serializer_class"
        action_serializer_class = getattr(self, action_serializer_name, None)
        if action_serializer_class:
            return action_serializer_class
        return super().get_serializer_class()
    
    # 通过many=True直接改造原有的API，使其可以批量创建
    # def get_serializer(self, *args, **kwargs):
    #     serializer_class = self.get_serializer_class()
    #     kwargs.setdefault('context', self.get_serializer_context())
    #     # 全部以可见字段为准
    #     can_see = self.get_menu_field(serializer_class)
    #     # 排除掉序列化器级的字段
    #     # sub_set = set(serializer_class._declared_fields.keys()) - set(can_see)
    #     # for field in sub_set:
    #     #     serializer_class._declared_fields.pop(field)
    #     # if not self.request.user.is_superuser:
    #     #     serializer_class.Meta.fields = can_see
    #     # 在分页器中使用
    #     self.request.permission_fields = can_see
    #     if isinstance(self.request.data, list):
    #         with transaction.atomic():
    #             return serializer_class(many=True, *args, **kwargs)
    #     else:
    #         return serializer_class(*args, **kwargs)
        
    def get_menu_field(self, serializer_class):
        """获取字段权限"""
        finded = False
        for model in get_custom_app_models():
            if model['object'] is serializer_class.Meta.model:
                finded = True
                break
        if finded is False:
            return []
        return MenuField.objects.filter(model=model['model']
        ).values('field_name', 'title')