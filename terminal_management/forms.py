# terminal_management/forms.py

from django import forms
from .models import ShipInfo, TerminalInfo, BaseStationInfo

class ShipInfoForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super(ShipInfoForm, self).__init__(*args, **kwargs)
        
        # 判断是否为编辑模式 (instance.pk 存在)
        if self.instance and self.instance.pk:
            # 1. 后端验证：将主键字段设置为非必填
            self.fields['mmsi'].required = False
            # 2. 前端展示：将输入框设置为只读
            self.fields['mmsi'].widget.attrs['readonly'] = True
        else:
            # 新建模式下，添加占位提示
            self.fields['mmsi'].widget.attrs['placeholder'] = '请输入9位MMSI号码'

    class Meta:
        model = ShipInfo
        fields = ['mmsi', 'ship_name', 'call_sign', 'ship_owner']
        widgets = {
            'mmsi': forms.TextInput(attrs={'class': 'form-control'}),
            'ship_name': forms.TextInput(attrs={'class': 'form-control'}),
            'call_sign': forms.TextInput(attrs={'class': 'form-control'}),
            'ship_owner': forms.TextInput(attrs={'class': 'form-control'}),
        }
        help_texts = {
            'mmsi': '船舶的唯一标识符，不可修改。',
            'call_sign': '船舶的唯一呼号，用于系统关联。',
        }

    def clean_call_sign(self):
        call_sign = self.cleaned_data.get('call_sign')
        if ShipInfo.objects.filter(call_sign=call_sign).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("该呼号已被其他船舶占用。")
        return call_sign

class TerminalInfoForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super(TerminalInfoForm, self).__init__(*args, **kwargs)
        
        if self.instance and self.instance.pk:
            # 应用同样的逻辑到 TerminalInfoForm
            self.fields['sn'].required = False
            self.fields['sn'].widget.attrs['readonly'] = True
        else:
            self.fields['sn'].widget.attrs['placeholder'] = '请输入设备的唯一SN码'

    class Meta:
        model = TerminalInfo
        fields = ['sn', 'ship', 'ip_address', 'port_number']
        widgets = {
            'sn': forms.TextInput(attrs={'class': 'form-control'}),
            'ship': forms.Select(attrs={'class': 'form-control'}),
            'ip_address': forms.TextInput(attrs={'class': 'form-control'}),
            'port_number': forms.NumberInput(attrs={'class': 'form-control'}),
        }
        help_texts = {
            'sn': '端站的唯一标识符，不可修改。',
        }

    def clean_sn(self):
        sn = self.cleaned_data.get('sn')
        if TerminalInfo.objects.filter(sn=sn).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("该SN码已被其他端站占用。")
        return sn

class BaseStationInfoForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super(BaseStationInfoForm, self).__init__(*args, **kwargs)
        
        if self.instance and self.instance.pk:
            # 应用同样的逻辑到 BaseStationInfoForm
            self.fields['bts_id'].required = False
            self.fields['bts_id'].widget.attrs['readonly'] = True
        else:
            self.fields['bts_id'].widget.attrs['placeholder'] = '请输入基站的唯一ID'

    class Meta:
        model = BaseStationInfo
        fields = '__all__'
        widgets = {
            'bts_id': forms.TextInput(attrs={'class': 'form-control'}),
            'bts_name': forms.TextInput(attrs={'class': 'form-control'}),
            'frequency_band': forms.TextInput(attrs={'class': 'form-control'}),
            'coverage_distance': forms.NumberInput(attrs={'class': 'form-control'}),
            'region_code': forms.TextInput(attrs={'class': 'form-control'}),
            'longitude': forms.NumberInput(attrs={'class': 'form-control', 'step': 'any'}),
            'latitude': forms.NumberInput(attrs={'class': 'form-control', 'step': 'any'}),
        }
        help_texts = {
            'bts_id': '基站的唯一标识符，不可修改。',
        }

    def clean_bts_name(self):
        bts_name = self.cleaned_data.get('bts_name')
        if BaseStationInfo.objects.filter(bts_name=bts_name).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("该基站名称已被其他基站占用。")
        return bts_name