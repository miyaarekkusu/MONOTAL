from django import forms
from .models import Community, Message, BoardCategory

class BoardCreateForm(forms.ModelForm):
    """
    掲示板作成フォーム
    """
    category = forms.ModelChoiceField(
        queryset=BoardCategory.objects.all(),
        label='カテゴリ',
        empty_label='カテゴリを選択してください',
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    class Meta:
        model = Community
        fields = ['name', 'description', 'category']
        widgets = {
            'name': forms.TextInput(attrs={'placeholder': '掲示板のタイトル（例：おすすめの機材について語ろう）', 'class': 'form-control'}),
            'description': forms.Textarea(attrs={'placeholder': 'この掲示板の目的やルールなどを分かりやすく入力してください。', 'rows': 5, 'class': 'form-control'}),
        }
        labels = {
            'name': 'タイトル',
            'description': '説明文',
        }

    def clean_name(self):
        name = self.cleaned_data.get('name')
        if not name:
            raise forms.ValidationError("タイトルは必須です。")
        if len(name) > 100:
            raise forms.ValidationError("タイトルは100文字以内で入力してください。")
        return name

    def clean_description(self):
        description = self.cleaned_data.get('description')
        if not description:
            raise forms.ValidationError("説明文は必須です。")
        if len(description) > 1000:
            raise forms.ValidationError("説明文は1000文字以内で入力してください。")
        return description


class MessageForm(forms.ModelForm):
    """
    メッセージ投稿フォーム
    """
    product_link = forms.ModelChoiceField(
        queryset=Product.objects.none(),  # ビューで動的に設定
        required=False,
        label="商品をリンク",
        empty_label="商品を選択..."
    )

    class Meta:
        model = Message
        fields = ['message_content', 'image', 'product_link']
        widgets = {
            'message_content': forms.Textarea(attrs={'placeholder': 'メッセージを入力...', 'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if user:
            # ログインユーザーが出品している貸出可能な商品のみをリストアップ
            self.fields['product_link'].queryset = Product.objects.filter(
                user=user, 
                delete_datetime__isnull=True,
                product_status_id=1 # 貸出可能
            ).order_by('-register_datetime')

    def clean(self):
        cleaned_data = super().clean()
        message_content = cleaned_data.get('message_content')
        image = cleaned_data.get('image')

        # テキストと画像の両方が空の場合はエラー
        if not message_content and not image:
            raise forms.ValidationError("メッセージを入力するか、画像を添付してください。")
        
        return cleaned_data
